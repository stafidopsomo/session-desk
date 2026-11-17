# Session Desk 0.3.0

Regular Windows x64 release: reference books and opt-in private hosting.

- Add source lists adventures and reference books from the existing local 5e.tools library. Reference books open in the reader and retain chapter order, images, source links, pins and manual preparation. Existing adventure identities are unchanged.
- Settings → Private hosting enables Tailscale Serve HTTPS on port 8443, with a stable private DM link. The main-PC browser edits the same host workspace; there is no database synchronisation or Git merge.
- Hosting keeps the host app running, resumes on its next launch and follows verified app updates. Disable revokes the link; Quit stops serving. The laptop must remain awake/online and Session Desk must be launched after reboot.
- Default is Off. The HTTP server stays on loopback; configured private origins retain DM/player authentication. Other Tailscale service configurations are preserved. Raw LAN/public hosting and Funnel are not enabled.
- Remote paths refer to the host laptop. Folder-picker and hosting controls belong on the host. Both PCs require Tailscale. Keep the DM link private; anyone with the link and network access can edit.

Use Settings → Check for updates → Download and install → Restart into update. Existing workspaces, files, fog, characters, Book records and source libraries are preserved. No repeat import is required. Back up before changing computers. PDF conversion/import, OCR and AI remain unavailable.

The unsigned package and same-host private HTTPS/browser checks do not certify a second physical device or complete source-map geometry. Those acceptance items remain deferred. First HTTPS certificate issuance may require additional time or Tailscale HTTPS setup.
