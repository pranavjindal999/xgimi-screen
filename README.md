# XGIMI Screen

Home Assistant controls for an XGIMI projector: screen off, brightness, and luminance boost.

Screen, brightness, and luminance boost are read from the projector every second. Changing them with the remote or the picture menu updates Home Assistant. Turning the screen switch off blanks the image. It does not shut the projector down.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pranavjindal999&repository=xgimi-screen&category=integration)

## Install

1. Click the button above. Home Assistant opens the repository in Marketplace, or in HACS on older versions. Install it.
2. Restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration**, and choose **XGIMI Screen**.

The projector on this network is `192.168.1.8`, port `5555`. Those values are already filled in.

The first connection asks the projector to allow network debugging. The picture has to be on to see **Allow USB debugging**. Choose **Allow**, and check **Always allow from this computer**.

## Controls

The projector appears as one device:

- **Screen** — on means the image is showing. Off means screen off. Audio and the system keep running.
- **Brightness** — the picture-menu slider, levels 1 through 10.
- **Luminance boost** — the extra toggle that drives the light past level 10.

If you change any of these on the projector, Home Assistant follows within about a second.

Network debugging has to stay enabled on the projector.
