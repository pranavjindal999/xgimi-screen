# XGIMI Screen

A Home Assistant switch for the XGIMI screen-off control: image off, projector still running.

The switch state is read from the projector every 5 seconds. Turning the screen off or on with the remote updates the switch. Turning the switch off does not shut the projector down.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pranavjindal999&repository=xgimi-screen&category=integration)

## Install

1. Click the button above. Home Assistant opens the repository in Marketplace, or in HACS on older versions. Install it.
2. Restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration**, and choose **XGIMI Screen**.

The projector on this network is `192.168.1.8`, port `5555`. Those values are already filled in.

The first connection asks the projector to allow network debugging. The picture has to be on to see **Allow USB debugging**. Choose **Allow**, and check **Always allow from this computer**.

## The switch

The device appears with one switch, **Screen**.

- **On** means the image is showing.
- **Off** means screen off. Audio and the system keep running.
- If you use the remote, the switch follows within about 5 seconds.

Network debugging has to stay enabled on the projector.
