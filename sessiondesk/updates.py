"""Explicit, verified side-by-side updates from the official public release feed.

No startup polling, installer scripts, imported workspace writes or automatic
restart. The HTTP controller schedules install() through TransferJobs and owns
an explicit restart after the current process releases its instance lock.
"""
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile

from . import __version__
from .importer import UserError
from .transfers import CHUNK, check_cancel, staging, remove_staging, recover_staging

REPOSITORY = 'stafidopsomo/session-desk'
LATEST = 'https://api.github.com/repos/' + REPOSITORY + '/releases/latest'
ORIGIN = 'https://github.com/' + REPOSITORY
HOSTS = frozenset(('api.github.com','github.com','release-assets.githubusercontent.com',
                   'objects.githubusercontent.com','github-releases.githubusercontent.com'))
MAX_PACKAGE = 256 * 1024 * 1024
MAX_EXPANDED = 512 * 1024 * 1024
STABLE = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')
SHA256 = re.compile(r'[0-9a-f]{64}')


def version_key(value):
    if not isinstance(value,str) or len(value)>100:
        raise UserError('Unsupported application version.')
    match=re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?',value)
    if not match:raise UserError('Unsupported application version.')
    prerelease=match[4]
    return (*map(int,match.group(1,2,3)),1 if prerelease is None else 0,
            tuple((0,int(x)) if x.isdigit() else (1,x) for x in (prerelease or '').split('.')))


def trusted_url(url):
    try:
        p=urlsplit(url)
        return p.scheme=='https' and p.hostname in HOSTS and p.port in (None,443) and not p.username and not p.password
    except (TypeError,ValueError):return False


class ReleaseRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not trusted_url(newurl):raise UserError('The update redirected to an unexpected download host.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def portable_path(name):
    if not isinstance(name,str) or not name or len(name)>600 or '\\' in name:
        raise UserError('Update archive contains an unsafe path.')
    path=PurePosixPath(name)
    if path.is_absolute() or any(part in ('','.','..') for part in name.split('/')):
        raise UserError('Update files must stay inside their application folder.')
    for part in path.parts:
        if (any(c in part for c in ':<>"|?*\x00\r\n') or part.endswith(('.',' '))
                or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',part)
                or part.lower() in ('.git','workspaces','credentials','imports')):
            raise UserError('Update archive contains an unsupported file path.')
    return path.as_posix()


class Updater:
    def __init__(self,root,current_version=__version__,frozen=None,opener=None):
        self.root=Path(root).resolve()
        self.current_version=current_version
        self.frozen=bool(getattr(sys,'frozen',False)) if frozen is None else bool(frozen)
        self.opener=opener or build_opener(ReleaseRedirect()).open
        self.available=None
        version_key(current_version)

    @property
    def applications(self):
        path=self.root/'applications'
        if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(self.root):
            raise UserError('Update application folder cannot be linked outside app data.')
        return path

    def recover(self):
        return recover_staging(self.applications,'_update-')

    def _response(self,url):
        if not trusted_url(url):raise UserError('Unsupported application update source.')
        return self.opener(Request(url,headers={'User-Agent':'SessionDesk-updates/'+self.current_version,
            'Accept':'application/vnd.github+json' if url==LATEST else 'application/octet-stream'}),timeout=25)

    @staticmethod
    def _http_error(exc,checking=False):
        if isinstance(exc,HTTPError) and exc.code in (403,429):
            return UserError('GitHub is limiting update requests. Try again later or download the release from GitHub.')
        return UserError('Update '+('check' if checking else 'download')+' failed. Check your connection and try again. Your application and workspaces were not changed.')

    def _read(self,url,limit,cancelled=lambda:False):
        try:
            with self._response(url) as response:
                if not trusted_url(response.geturl()):raise UserError('Unexpected application update redirect.')
                chunks=[];size=0
                while True:
                    check_cancel(cancelled);chunk=response.read(min(CHUNK,limit+1-size))
                    if not chunk:break
                    size+=len(chunk)
                    if size>limit:raise UserError('Update response exceeds the supported size.')
                    chunks.append(chunk)
                return b''.join(chunks)
        except (HTTPError,URLError,TimeoutError,OSError) as exc:
            raise self._http_error(exc,checking=url==LATEST) from exc

    def check(self):
        self.available=None
        try:
            payload=self._read(LATEST,2*1024*1024)
        except UserError as exc:
            if isinstance(exc.__cause__,HTTPError) and exc.__cause__.code==404:
                return {'available':False,'can_install':self.frozen,'supported':self.frozen,'current':self.current_version,'latest':None,'current_version':self.current_version,
                        'message':'No regular release is available yet. Preview releases are not installed automatically.'}
            raise
        try:
            data=json.loads(payload.decode('utf-8'))
            tag=data['tag_name'];version=tag.removeprefix('product-v')
            if (tag!='product-v'+version or not STABLE.fullmatch(version)
                    or data.get('draft') is not False or data.get('prerelease') is not False):
                raise ValueError('Not a regular release')
            filename='SessionDesk-'+version+'-windows-x64.zip'
            base=ORIGIN+'/releases/download/'+tag+'/'
            matches={name:[a for a in data['assets'] if a.get('name')==name] for name in (filename,filename+'.sha256')}
            if any(len(rows)!=1 for rows in matches.values()):raise ValueError('Missing assets')
            package=matches[filename][0];checksum=matches[filename+'.sha256'][0]
            if (package['browser_download_url']!=base+filename or checksum['browser_download_url']!=base+filename+'.sha256'
                    or type(package.get('size')) is not int or not 0<package['size']<=MAX_PACKAGE
                    or type(checksum.get('size')) is not int or not 0<checksum['size']<=4096):
                raise ValueError('Unexpected assets')
            digest=package.get('digest')
            if digest is not None and (not isinstance(digest,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',digest)):
                raise ValueError('Unsupported asset digest')
        except (ValueError,TypeError,KeyError,AttributeError,UnicodeError) as exc:
            raise UserError('The latest GitHub release has no supported verified Windows package. Use its release page or try again later.') from exc
        newer=version_key(version)>version_key(self.current_version)
        result={'available':newer,'can_install':self.frozen,'supported':self.frozen,'current':self.current_version,'latest':version,'current_version':self.current_version,
                'version':version,'release_url':ORIGIN+'/releases/tag/'+tag,'size':package['size'],
                'message':'Update available.' if newer else 'You are up to date.'}
        if newer:self.available={'version':version,'filename':filename,'url':base+filename,
                                'checksum_url':base+filename+'.sha256','size':package['size'],
                                'digest':None if digest is None else digest.split(':',1)[1]}
        return result

    def _download(self,release,destination,cancelled,progress):
        total=release['size'];count=0;digest=hashlib.sha256()
        try:
            with self._response(release['url']) as source,destination.open('xb') as out:
                if not trusted_url(source.geturl()):raise UserError('Unexpected application update redirect.')
                while True:
                    check_cancel(cancelled);chunk=source.read(CHUNK)
                    if not chunk:break
                    count+=len(chunk)
                    if count>total or count>MAX_PACKAGE:raise UserError('Update download exceeds its published size.')
                    out.write(chunk);digest.update(chunk);progress('Downloading update',count,total)
            if count!=total:raise UserError('Update download was interrupted. Retry the update.')
            return digest.hexdigest()
        except (HTTPError,URLError,TimeoutError,OSError) as exc:
            raise self._http_error(exc) from exc

    @staticmethod
    def _extract(archive,content,version,cancelled,progress):
        try:
            with zipfile.ZipFile(archive) as z:
                infos=z.infolist();names=[portable_path(i.filename) for i in infos]
                if (len(infos)>10000 or len({n.casefold() for n in names})!=len(names)
                        or sum(i.file_size for i in infos)>MAX_EXPANDED
                        or any(i.is_dir() or i.flag_bits&1 or (i.external_attr>>16)&0o170000==0o120000 for i in infos)):
                    raise UserError('Update archive has duplicate/linked/encrypted entries or exceeds supported limits.')
                info=z.getinfo('MANIFEST.json')
                if info.file_size>4*1024*1024:raise UserError('Update manifest exceeds its supported size.')
                manifest=json.loads(z.read(info))
                if (manifest.get('version')!=version or manifest.get('target')!='windows-x64'
                        or manifest.get('dirty_source') is not False or manifest.get('ai') is not False
                        or not re.fullmatch(r'[0-9a-f]{40}',str(manifest.get('commit','')))
                        or not SHA256.fullmatch(str(manifest.get('product_digest','')))):
                    raise UserError('Update package provenance does not match the published Windows release.')
                records=manifest['files']
                if not isinstance(records,list) or not records or len(records)>10000:
                    raise UserError('Invalid update file manifest.')
                expected={portable_path(r['path']):r for r in records}
                if (len(expected)!=len(records) or 'SessionDesk.exe' not in expected
                        or set(names)!=set(expected)|{'MANIFEST.json'}):
                    raise UserError('Update archive differs from its explicit file manifest.')
                by_name={i.filename:i for i in infos};done=0;total=sum(i.file_size for i in infos)
                for name in names:
                    check_cancel(cancelled)
                    item=by_name[name];record=expected.get(name)
                    if record and (type(record.get('size')) is not int or record['size']!=item.file_size
                                   or not SHA256.fullmatch(str(record.get('sha256','')))):
                        raise UserError('Invalid update file metadata.')
                    target=content/name
                    if not target.resolve().is_relative_to(content.resolve()):raise UserError('Update path leaves its staging folder.')
                    target.parent.mkdir(parents=True,exist_ok=True)
                    digest=hashlib.sha256()
                    with z.open(item) as inp,target.open('xb') as out:
                        while chunk:=inp.read(CHUNK):
                            check_cancel(cancelled);out.write(chunk);digest.update(chunk);done+=len(chunk)
                            progress('Verifying and extracting update',done,total)
                    if record and digest.hexdigest()!=record['sha256']:
                        raise UserError('Update file checksum failed. Nothing was installed.')
        except (zipfile.BadZipFile,ValueError,TypeError,KeyError,UnicodeError) as exc:
            raise UserError('Update package is malformed or incomplete. Nothing was installed.') from exc

    @staticmethod
    def _same_install(existing,verified,cancelled,progress):
        # A crash can lose the pending-restart response after files committed.
        # Compare against a freshly authenticated download, not an old receipt
        # or an editable manifest in the existing installation.
        def inventory(root):
            result={};pending=[root]
            while pending:
                folder=pending.pop()
                if folder.is_symlink() or folder.is_junction():
                    raise UserError('An existing update folder contains a link and was not reused.')
                for item in folder.iterdir():
                    check_cancel(cancelled)
                    if item.is_symlink() or item.is_junction():
                        raise UserError('An existing update contains linked files and was not reused.')
                    if item.is_dir():pending.append(item)
                    elif item.is_file():
                        before=item.stat();digest=hashlib.sha256()
                        with item.open('rb') as source:
                            while chunk:=source.read(CHUNK):
                                check_cancel(cancelled);digest.update(chunk)
                        after=item.stat()
                        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
                            raise UserError('An installed update changed during verification. Retry after closing it.')
                        result[item.relative_to(root).as_posix()]=(after.st_size,digest.hexdigest())
                    else:raise UserError('An existing update contains unsupported files.')
            return result
        progress('Verifying an already installed update',0,0)
        try:return inventory(existing)==inventory(verified)
        except OSError as exc:
            raise UserError('The existing update could not be verified. Close its files or use the GitHub download.') from exc

    def install(self,release=None,cancelled=lambda:False,progress=lambda *_:None,on_commit=lambda:None):
        if not self.frozen:raise UserError('Automatic installation is available in the Windows EXE. Update a source checkout with Git instead.')
        selected=copy.deepcopy(self.available)
        if not selected or release is not None and (not isinstance(release,dict) or release.get('version')!=selected['version']):
            raise UserError('Check for updates before installing the available release.')
        apps=self.applications;apps.mkdir(parents=True,exist_ok=True)
        destination=apps/selected['version']
        if destination.is_symlink() or destination.is_junction() or destination.exists() and not destination.is_dir():
            raise UserError('The existing update destination is not a regular application folder.')
        check_cancel(cancelled);self.recover();pending=staging(apps,'_update-');content=pending/'content';content.mkdir()
        try:
            try:checksum=self._read(selected['checksum_url'],4096,cancelled).decode('utf-8-sig').split()
            except UnicodeError as exc:raise UserError('The published update checksum is invalid.') from exc
            if len(checksum)!=2 or not SHA256.fullmatch(checksum[0]) or checksum[1]!=selected['filename']:
                raise UserError('The published update checksum is missing or invalid.')
            actual=self._download(selected,pending/'package.zip',cancelled,progress)
            if actual!=checksum[0] or selected['digest'] is not None and actual!=selected['digest']:
                raise UserError('Update checksum failed. Nothing was installed.')
            self._extract(pending/'package.zip',content,selected['version'],cancelled,progress)
            check_cancel(cancelled)
            reused=destination.exists()
            if destination.is_symlink() or destination.is_junction() or reused and not destination.is_dir():
                raise UserError('Update destination changed. Nothing was replaced.')
            if reused and not self._same_install(destination,content,cancelled,progress):
                raise UserError('The existing update differs from the verified release. It was left unchanged; use a separate GitHub download.')
            check_cancel(cancelled)
            on_commit()
            if not reused:content.rename(destination)
            return {'version':selected['version'],'path':str(destination),
                    'executable':str(destination/'SessionDesk.exe'),'restart_required':True}
        finally:
            try:remove_staging(apps,pending,'_update-')
            except (OSError,UserError):pass


def _installed_target(root, executable, manifest_digest=None):
    root=Path(root).resolve();apps=root/'applications';exe=Path(executable)
    if apps.is_symlink() or apps.is_junction() or exe.is_symlink():
        raise UserError('Updated application cannot be linked.')
    exe=exe.resolve()
    folder=exe.parent
    if (exe.name!='SessionDesk.exe' or folder.parent!=apps
            or not STABLE.fullmatch(folder.name) or folder.is_symlink() or folder.is_junction()):
        raise UserError('Invalid updated application location.')
    manifest=folder/'MANIFEST.json'
    raw=manifest.read_bytes()
    if len(raw)>4*1024*1024 or manifest_digest and hashlib.sha256(raw).hexdigest()!=manifest_digest:
        raise UserError('Updated application manifest changed.')
    data=json.loads(raw)
    if data.get('version')!=folder.name or data.get('target')!='windows-x64' or data.get('dirty_source') is not False:
        raise UserError('Updated application metadata is invalid.')
    for record in data['files']:
        file=folder/portable_path(record['path'])
        if not file.resolve().is_relative_to(folder.resolve()) or file.is_symlink() or file.is_junction():
            raise UserError('Updated application file leaves its installation.')
        if file.stat().st_size!=record['size']:
            raise UserError('Updated application file changed.')
        with file.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=record['sha256']:
                raise UserError('Updated application file changed.')
    if not exe.is_file():
        raise UserError('Updated application executable is missing.')
    return data['version'],hashlib.sha256(raw).hexdigest()


def activate_application(root, executable):
    """Persist the explicit restart choice so original EXE/shortcuts stay usable."""
    root=Path(root).resolve();exe=Path(executable).absolute()
    version,digest=_installed_target(root,exe)
    pointer=root/'active-application.json';temp=pointer.with_suffix('.tmp')
    if pointer.is_symlink() or temp.is_symlink():
        raise UserError('Application launch preference cannot be linked.')
    temp.write_text(json.dumps({'version':version,'executable':str(exe),'manifest_sha256':digest}),encoding='utf-8')
    temp.replace(pointer)


def preferred_application(root, current_version):
    """Ignore invalid launch pointers and fall back to the current working build."""
    try:
        pointer=Path(root)/'active-application.json'
        if pointer.is_symlink() or pointer.stat().st_size>10000:return None
        selected=json.loads(pointer.read_text(encoding='utf-8'))
        if version_key(selected['version'])<=version_key(current_version):return None
        version,_=_installed_target(root,selected['executable'],selected['manifest_sha256'])
        return Path(selected['executable']) if version==selected['version'] else None
    except (OSError,ValueError,KeyError,TypeError,UserError):
        return None
