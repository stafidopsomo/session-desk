"""Background operations and private transfer files, independent of HTTP/UI routes."""
from contextlib import contextmanager
from pathlib import Path
import threading
import uuid

from .importer import UserError
from .transfers import ACTIVE, CHUNK, MAX_BACKUP, check_cancel, staging, remove_staging, recover_staging


class TransferJobs:
    def __init__(self, store):
        self.store = store
        self.jobs = {}
        self.lock = threading.RLock()
        self.transfer_root = store.root / 'transfers'
        self.active_downloads = 0
        self.accepting = True

    def _new_job(self, kind, state='running'):
        with self.lock:
            if not self.accepting:
                raise UserError('The app is closing. Reopen Session Desk to start another operation.')
            if any(x['state'] in ACTIVE for x in self.jobs.values()):
                raise UserError('Another operation is running. Wait or cancel it first.')
            jid = str(uuid.uuid4())
            event = threading.Event()
            job = {"id": jid, "kind": kind, "state": state, "cancel": event,
                   "message": "Starting " + kind, "done": 0, "total": 0}
            self.jobs[jid] = job
            return job

    def public_job(self, job):
        keys = ('id', 'kind', 'state', 'message', 'done', 'total', 'result', 'error', 'error_code')
        return {k: job[k] for k in keys if k in job} | {'cancel_requested': job['cancel'].is_set()}

    def _clean_job(self, job):
        with self.lock:
            folder = job.get('folder')
            if folder is None:
                return
            try:
                remove_staging(self.transfer_root, folder, '_transfer-')
            except (OSError, UserError):
                # Windows antivirus/indexers may briefly hold a private file.
                # Keep the marked folder for retry/startup recovery; cleanup
                # cannot change a committed result or strand a running job.
                job['cleanup_pending'] = True
            else:
                job.pop('folder', None)
                job.pop('cleanup_pending', None)

    def _run_job(self, job, operation):
        event, kind = job['cancel'], job['kind']
        def progress(message, done=0, total=0):
            with self.lock:
                job.update(message=message, done=done, total=total)

        def run():
            try:
                result = operation(event, job, progress)
                with self.lock:
                    job.update(state="complete", result=result)
            except Exception as exc:
                with self.lock:
                    job.update(state="cancelled" if event.is_set() else "failed",
                               error=str(exc) if isinstance(exc, UserError) else
                               "Operation stopped. Check source files, folder permissions and available space.",
                               error_code=kind.upper() + "_" + type(exc).__name__.upper())
            finally:
                if kind != 'export' or job['state'] != 'complete':
                    self._clean_job(job)
        threading.Thread(target=run, daemon=True).start()
        return self.public_job(job)

    def start_job(self, kind, operation):
        return self._run_job(self._new_job(kind), operation)

    def commit(self, event, job):
        with self.lock:
            check_cancel(event.is_set)
            job['state'] = 'committing'

    def cancel_job(self, job):
        with self.lock:
            if job['state'] in ('running', 'uploading'):
                job['cancel'].set()
                if job['state'] == 'uploading' and not job.get('upload_claimed'):
                    self._clean_job(job)
                    job['state'] = 'cancelled'
                    job['error'] = 'Backup upload cancelled.'
        return self.public_job(job)

    def start_export(self, wid):
        self.store.folder(wid)
        with self.lock:
            ready = [j for j in self.jobs.values() if j['kind'] == 'export' and j['state'] == 'complete'
                     and 'folder' in j and not j.get('downloads')]
            for old in ready[:-1]:
                self._clean_job(old)
        def operation(event, job, progress):
            job['folder'] = staging(self.transfer_root, '_transfer-')
            destination = job['folder'] / 'workspace.zip'
            self.store.backup_file(wid, destination, event.is_set, progress)
            check_cancel(event.is_set)
            return {'download': job['id'], 'filename': 'sessiondesk-workspace.zip', 'size': destination.stat().st_size}
        return self.start_job('export', operation)

    def prepare_restore(self, size):
        if type(size) is not int or not 0 < size <= MAX_BACKUP:
            raise UserError('Choose a workspace ZIP up to 1 GB plus metadata.')
        job = self._new_job('restore', 'uploading')
        try:
            job['folder'] = staging(self.transfer_root, '_transfer-')
            job.update(total=size, message='Uploading workspace backup')
            return self.public_job(job)
        except Exception:
            job['state'] = 'failed'
            raise

    def receive_restore(self, jid, input_stream, length):
        with self.lock:
            job = self.jobs.get(jid)
            if not job or job['kind'] != 'restore' or job['state'] != 'uploading' or job.get('upload_claimed'):
                raise UserError('Restore upload is not available. Start a new restore.')
            if length != job['total']:
                self.cancel_job(job)
                raise UserError('Backup upload size does not match the selected file.')
            job['upload_claimed'] = True
        try:
            path = job['folder'] / 'upload.zip'
            received = 0
            with path.open('xb') as output:
                while received < length:
                    check_cancel(job['cancel'].is_set)
                    chunk = input_stream.read(min(CHUNK, length - received))
                    if not chunk:
                        raise UserError('Backup upload was interrupted. Retry with the same ZIP.')
                    output.write(chunk)
                    received += len(chunk)
                    with self.lock:
                        job['done'] = received
            check_cancel(job['cancel'].is_set)
            with self.lock:
                job.update(state='running', message='Validating workspace backup', done=0)
            return self._run_job(job, lambda event, current, progress: self.store.restore_file(
                path, event.is_set, progress, lambda: self.commit(event, current)))
        except Exception as exc:
            self._clean_job(job)
            with self.lock:
                job.update(state='cancelled' if job['cancel'].is_set() else 'failed',
                           error=str(exc) if isinstance(exc, UserError) else 'Backup upload stopped. Retry the file.')
            raise

    @contextmanager
    def download(self, jid):
        with self.lock:
            job = self.jobs.get(jid)
            if not job or job['kind'] != 'export' or job['state'] != 'complete' or 'folder' not in job:
                raise UserError('Backup is no longer cached. Export it again.')
            job['downloads'] = job.get('downloads', 0) + 1
            self.active_downloads += 1
            file = job['folder'] / 'workspace.zip'
        try:
            yield file
        finally:
            with self.lock:
                self.active_downloads -= 1
                job['downloads'] -= 1
                if job.get('discard') and not job['downloads']:
                    self._clean_job(job)

    def recover(self):
        return self.store.recover_interrupted_restores() + recover_staging(self.transfer_root, '_transfer-')

    def close(self):
        with self.lock:
            self.accepting = False
            for job in list(self.jobs.values()):
                if job['state'] in ACTIVE:
                    self.cancel_job(job)
                elif not job.get('downloads'):
                    self._clean_job(job)

    def status(self, jid, cancel=False):
        with self.lock:
            job = self.jobs.get(jid)
            if not job:
                raise UserError('Operation not found. Restart it after reopening the app.')
            return self.cancel_job(job) if cancel else self.public_job(job)

    def discard(self, jid):
        with self.lock:
            job = self.jobs.get(jid)
            if job and job['state'] not in ACTIVE:
                job['discard'] = True
                if not job.get('downloads'):
                    self._clean_job(job)
        return {'ok': True}

    def busy(self):
        with self.lock:
            return bool(self.active_downloads or any(j['state'] in ACTIVE for j in self.jobs.values()))

    def request_close(self):
        with self.lock:
            if self.busy():
                raise UserError('Wait for the current operation/download to finish, or cancel it before quitting.')
            self.accepting = False

    def cancel_and_idle(self):
        with self.lock:
            for job in self.jobs.values():
                self.cancel_job(job)
            if self.busy():
                return False
            self.accepting = False
            return True

