# Hardware Recommendations

## Fitness Dashboard — Raspberry Pi 4 4GB

**Purpose:** Runs the fitness dashboard Docker Compose stack (FastAPI, SQLite, ntfy).

### Option A — CanaKit Bundle (easiest)
Includes board, power supply, case, and SD card in one order.

| Item | Amazon |
|---|---|
| CanaKit Pi 4 4GB Basic Kit | [amazon.com/dp/B07TXKY4Z9](https://www.amazon.com/CanaKit-Raspberry-4GB-Basic-Kit/dp/B07TXKY4Z9) |

### Option B — Board only + separate accessories
If you want to pick your own case or go PoE.

| Item | Amazon |
|---|---|
| Pi 4 4GB (board) | [amazon.com/dp/B09TTNF8BT](https://www.amazon.com/Raspberry-Pi-RPI4-MODBP-4GB-Model-4GB/dp/B09TTNF8BT) |
| Official PoE+ HAT (optional, replaces PSU) | [pishop.us](https://www.pishop.us/product/raspberry-pi-poe-plus-hat/) |
| 32GB SanDisk Endurance MicroSD | Search: "SanDisk MAX Endurance 32GB microSD" on Amazon |

**Notes:**
- If using the PoE+ HAT, you need a case that fits with a HAT attached (the official Pi case won't fit)
- Only buy from "Sold by Amazon" or CanaKit — counterfeit Pi boards exist on Amazon
- Pi 4 4GB will remain in production until at least January 2034

---

## AdGuard DNS — Raspberry Pi Zero 2W + PoE Ethernet

**Purpose:** Dedicated DNS filtering with AdGuard Home. Always-on, single cable (PoE).

| Item | Amazon | Notes |
|---|---|---|
| Pi Zero 2W (no headers) | [amazon.com/dp/B09LH5SBPS](https://www.amazon.com/Raspberry-Zero-Bluetooth-RPi-2W/dp/B09LH5SBPS) | No headers needed — HAT uses pogo pins |
| Waveshare PoE/ETH/USB HAT with ABS case | [amazon.com/dp/B09PZY3HGV](https://www.amazon.com/waveshare-PoE-USB-HUB-802-3af-Compliant/dp/B09PZY3HGV) | Case included, ethernet + PoE + 3x USB |
| 32GB SanDisk Endurance MicroSD | Search: "SanDisk MAX Endurance 32GB microSD" on Amazon | |

**Notes:**
- The Waveshare HAT connects via pogo pins to the underside of the board — pre-soldered headers are not required
- 100Mbps ethernet is more than sufficient for DNS
- 802.3af PoE — compatible with all current Unifi switches
- 512MB RAM is plenty for dedicated AdGuard Home

---

## Shared Requirements

- **Tailscale** — install on both Pis and your Android phone (free, no hardware needed)
- **MicroSD cards** — SanDisk Endurance series recommended over standard cards for always-on Pi use (designed for continuous write operations)

---

## What to Buy from Where

| Seller | Notes |
|---|---|
| Amazon (Sold by Amazon) | Fine for official Pi boards and accessories |
| CanaKit on Amazon | Authorized reseller, safe |
| Adafruit | Reliable, good HAT/accessory selection |
| PiShop.us | Good stock, US-based |
| Avoid | Random Amazon third-party sellers for Pi boards |
