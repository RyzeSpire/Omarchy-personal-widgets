# Spotify widget

Click the bar icon to control Spotify while its desktop player runs in the hidden Spotify workspace. The bar icon is green when the local Spotify player is available (including when paused) and red when it is closed; status updates through MPRIS even with the popup closed.

- Playlists opens your library. Select a playlist to browse its artwork, owner, song count, duration and searchable song list. Selecting a playlist does not change playback.
- Click Play playlist or a song to play it on this computer. Song selection preserves the playlist as the playback context. The back arrow returns to your library.
- Queue opens or closes the side panel. It shows Now Playing and Spotify's upcoming queue; it refreshes when tracks change, every 15 seconds while open, or with the refresh button. Click an upcoming song to jump to it while retaining the playlist and remaining queue order. Rows briefly disable while Spotify confirms the jump. On narrow displays it moves below the player.
- The volume slider changes Spotify's own volume. The speaker button mutes and restores the previous level.
- Shuffle cycles off/on. Repeat cycles off/single song/playlist. Smart Shuffle integration is deferred.
- Quit Spotify opens an inline confirmation with Cancel and Quit Spotify. Confirming stops playback, quits the hidden desktop player, closes the widget popup, and leaves workspace 0 if it is empty. Escape cancels the confirmation.
- Open Spotify shows the full app on workspace 0. Open in Spotify in a playlist view also navigates to that playlist.

Queue reading and song selection use the existing OAuth PKCE connection with playback read/control permissions. Enable playback access reconnects the same developer app if needed. Credentials remain in the existing private state directory and are never emitted by the helpers.

Spotify restricts playlist contents in development mode to playlists owned by the account or collaborated on. Other playlists can be opened in the full app. Upcoming queue length is whatever Spotify's API returns. Playlist editing and Mix remain in the full Spotify app.

When starting Spotify from a closed state, the background helper waits for the desktop window to map and keeps parking it on the hidden Spotify workspace during a short startup settling period. This prevents an early MPRIS readiness signal from leaving a later window visible. Open Spotify still deliberately reveals the full app on workspace 0.

Playlists containing local tracks are supported through Spotify itself. The widget reads Spotify playlist metadata, labels local songs, and selects them with the playlist context and original position using the Web API. It never scans, opens, decodes or plays music files. Spotify desktop must already index the files and have the needed codecs. Current local-track highlighting accepts Spotify's local URLs from MPRIS. Queue Now Playing falls back to Spotify's playback state when its queue endpoint omits local songs; the upcoming queue is marked unavailable if Spotify does not supply it.
