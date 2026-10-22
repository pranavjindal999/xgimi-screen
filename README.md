# XGIMI Screen

Home Assistant controls for an XGIMI projector: standby, screen off, brightness, luminance boost, and volume.

The controls are read from the projector every second. Changing them with the remote or the picture menu updates Home Assistant. Power off is standby, the same as a short press of the remote power button. It does not shut the projector down. Screen off only blanks the image.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pranavjindal999&repository=xgimi-screen&category=integration)

## Install

1. Click the button above. Home Assistant opens the repository in Marketplace, or in HACS on older versions. Install it.
2. Restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration**, and choose **XGIMI Screen**.

The projector on this network is `192.168.1.8`, port `5555`. Those values are already filled in.

The first connection asks the projector to allow network debugging. The picture has to be on to see **Allow USB debugging**. Choose **Allow**, and check **Always allow from this computer**.

## One card

After a restart, refresh the browser. Add a card and choose **XGIMI Screen**. Pick the **Screen** entity. The card shows power, screen, brightness, luminance boost, and volume together.

## Controls

The projector appears as one device:

- **Power** — on means the projector is running. Off is standby, not shutdown. Waking can take several seconds.
- **Screen** — on means the image is showing. Off blanks the image. Audio and the system keep running.
- **Brightness** — the picture-menu slider, levels 1 through 10.
- **Luminance boost** — the extra toggle that drives the light past level 10.
- **Volume** — the remote volume rocker, from 0 to 100.

If you change any of these on the projector, Home Assistant follows within about a second.

Network debugging has to stay enabled on the projector.
