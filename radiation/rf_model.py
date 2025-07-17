import numpy as np
from scipy.special import erfc
from skyfield.api import Topos, EarthSatellite, load
import datetime
import io
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from plot_utils import DEFAULT_FIGSIZE

VERBOSE = True  # Set to False for silent operation except summary

antennas = [
    # VHF (30 MHz - 300 MHz)
    {
        "name": "FAKE VHF Yagi Antenna",
        "frequency_range": (30e6, 300e6),
        "gain": 7,
        "type": "Yagi-Uda",
    },
    # UHF (300 MHz - 1 GHz)
    {
        "name": "FAKE UHF Log-Periodic Dipole Array",
        "frequency_range": (300e6, 1e9),
        "gain": 10,
        "type": "Log-Periodic",
    },
    {
        "name": "FAKE UHF Patch Antenna",
        "frequency_range": (300e6, 1e9),
        "gain": 8,
        "type": "Patch",
    },
    # L-Band (1 GHz - 2 GHz)
    {
        "name": "FAKE L-Band Helical Antenna",
        "frequency_range": (1e9, 2e9),
        "gain": 12,
        "type": "Helical",
    },
    {
        "name": "FALCCON - RW",
        "frequency_range": (1e9, 2e9),
        "gain": 21,
        "type": "Dipole Array",
    },
    {
        "name": "L Band Patch Antenna - Printech",
        "frequency_range": (1.563e9, 1.587e9),
        "gain": 5,
        "type": "Patch",
    },
    # S-Band (2 GHz - 4 GHz)
    {
        "name": "AC-2000 - AAC",
        "frequency_range": (2e9, 2.3e9),
        "gain": 5.2,
        "type": "Parabolic Dish",
        "vswr": {
            "frequency": [2e9, 2.3e9],  # Frequencies in Hz
            "vswr_values": [1.5, 1.5],  # VSWR values
        },
    },
    {
        "name": "SANT S-band Patch Antenna - AAC",
        "frequency_range": (2.2e9, 2.29e9),
        "gain": 7,
        "type": "Patch",
        "connector": "SMA_P",
        "s11_dB": -15,
    },
    {
        "name": "Quad S Band Antenna - IQ Tech",
        "frequency_range": (1.98e9, 2.5e9),
        "gain": 11,
        "type": "Patch Array",
        "vswr": {
            "frequency": [1.98e9, 2.5e9],  # Frequencies in Hz
            "vswr_values": [1.8, 1.8],  # VSWR values, check data sheet
        },
    },
    {
        "name": "S-Band Antenna Commercial - Enduro",
        "frequency_range": (2.025e9, 2.11e9),
        "gain": 7,
        "type": "Patch array",
        "vswr": {
            "frequency": [2.025e9, 2.11e9],  # Frequencies in Hz
            "vswr_values": [1.8, 1.8],  # VSWR values, check data sheet
        },
    },
    {
        "name": "S-Band Antenna Wideband - Enduro",
        "frequency_range": (2.2e9, 2.29e9),
        "gain": 5,
        "type": "Patch array",
        "vswr": {
            "frequency": [2.025e9, 2.11e9],  # Frequencies in Hz
            "vswr_values": [1.8, 1.8],  # VSWR values, check data sheet
        },
    },
    # C-Band (4 GHz - 8 GHz)
    {
        "name": "FAKE C-Band Horn Antenna",
        "frequency_range": (4e9, 8e9),
        "gain": 18,
        "type": "Horn",
    },
    # X-Band (8 GHz - 12 GHz)
    {
        "name": "X-Band Patch Antenna - Enduro",
        "frequency_range": (8.025e9, 8.4e9),
        "gain": 6,
        "type": "Patch",
    },
    {
        "name": "4x4 X-Band Patch Array - Enduro",
        "frequency_range": (8.025e9, 8.4e9),
        "gain": 16,
        "type": "Patch Array",
    },
    {
        "name": "XANT X-Band Patch Antenna - Cubecom",
        "frequency_range": [8e9, 8.4e9],  # Frequency range in Hz
        "gain": 8,
        "type": "Patch",
        "return_loss": {
            "frequency": [8.0e9, 8.1e9, 8.2e9, 8.3e9, 8.4e9],  # Frequencies in Hz
            "return_loss_dB": [-21, -20, -18, -16, -17],  # Return loss in dB
        },
    },
    {
        "name": "XPLANT X-band Payload Antenna - Cubecom",
        "frequency_range": (8.5e9, 9.6e9),
        "gain": 8,
        "type": "Patch Array",
        "return_loss": {
            "frequency": [8.50e9, 8.75e9, 8.90e9, 9.00e9, 9.25e9, 9.50e9],
            "return_loss_dB": [-10, -20, -15, -25, -30, -10],
        },
    },
    {
        "name": "High Gain X-Band Antenna - Anywaves",
        "frequency_range": (7.9e9, 8.5e9),
        "gain": 15.5,
        "type": "Patch array",
        "return_loss": {
            "frequency": [7.9e9, 8.5e9],
            "return_loss_dB": [-10, -10],  # made up, no data
        },
    },
    {
        "name": "High-Gain X-Band Patch Array - Printech",
        "frequency_range": [7.5e9, 8.5e9],  # Frequency range in Hz
        "gain": 20.7,  # Gain in dB
        "type": "Patch Array",
        "vswr": {
            "frequency": [
                7.5e9,
                7.6e9,
                7.7e9,
                7.8e9,
                7.9e9,
                8.0e9,
                8.1e9,
                8.2e9,
                8.3e9,
                8.4e9,
            ],  # Frequencies in Hz
            "vswr_values": [
                1.3,
                1.4,
                1.2,
                1.5,
                1.3,
                1.6,
                1.2,
                1.8,
                1.4,
                2.5,
            ],  # VSWR values
        },
    },
    {
        "name": "Lens Horn Antenna - Anteral",
        "frequency_range": (8.2e9, 12.4e9),
        "gain": 30.4,
        "type": "Lens Horn",
        "s11_dB": -18,
    },  # not trusted?
    # Ku-Band (12 GHz - 18 GHz)
    {
        "name": "FAKE Ku-Band Microstrip Antenna",
        "frequency_range": (12e9, 18e9),
        "gain": 23,
        "type": "Microstrip",
    },
    # K-Band (18 GHz - 27 GHz)
    {
        "name": "FAKE K-Band Waveguide Antenna",
        "frequency_range": (18e9, 27e9),
        "gain": 25,
        "type": "Waveguide",
    },
    {
        "name": "K-Band 4x4 Patch Array - Enduro",
        "frequency_range": (17.7e9, 20.2e9),
        "gain": 16,
        "type": "Waveguide",
    },
    # Ka-Band (27 GHz - 40 GHz)
    {
        "name": "FAKE Ka-Band Horn Antenna",
        "frequency_range": (27e9, 40e9),
        "gain": 30,
        "type": "Horn",
    },
    {
        "name": "PAN-5151-64-KA - ReliaSat",
        "frequency_range": (27e9, 31e9),
        "gain": 20,
        "type": "Panel Array",
    },
    {
        "name": "4x4 X-Band Patch Array - Enduro",
        "frequency_range": (8.025e9, 8.4e9),
        "gain": 16,
        "type": "Patch Array",
    },
    # Above 40 GHz (EHF - Millimeter Wave Frequencies)
    {
        "name": "FAKE EHF Lens Antenna",
        "frequency_range": (40e9, 60e9),
        "gain": 35,
        "type": "Lens",
    },
    {
        "name": "FAKE Terahertz Horn Antenna",
        "frequency_range": (60e9, 100e9),
        "gain": 40,
        "type": "Horn",
    },
]


def interpolate_return_loss(frequency, antenna_data):
    freq_points = antenna_data["return_loss"]["frequency"]
    loss_values = antenna_data["return_loss"]["values"]
    return np.interp(frequency, freq_points, loss_values)


modulation_bits_per_symbol = {
    "OOK": 1,
    "BPSK": 1,
    "QPSK": 2,
    "GMSK": 1,
    "MSK": 1,
    "2FSK": 1,
    "4FSK": 2,
    "2GFSK": 1,
    "4GFSK": 2,
    "8PSK": 3,
    "16QAM": 4,
    "16APSK": 4,
    "32APSK": 5,
    "256APSK": 8,
    "GFSK": 1,
    "FSK": 1,
}

modems_sdrs = [
    {
        "type": "receiver",
        "name": "RX-2000 S-Band Receiver - AAC",
        "data_rate": (9.6, 153.6),  # kbps
        "modulations": ["FM", "GFSK"],
        "receive_sensitivity_dBm": -110,  # -117 @ 9.6kbps
        "rx_frequency_range": (2000e6, 2400e6),  # Hz
        "rx_ant_con": "SMA",
        "interface": "Micro-D",
    },
    {
        "type": "transceiver",
        "name": "UHF Transceiver II - Enduro",
        "data_rate": (0.1, 19.2),  # kbps
        "modulations": ["OOK", "GMSK", "2FSK", "4FSK", "4GFSK"],
        "transmit_power_W": [1, 2],  # Watts
        "receive_sensitivity_dBm": -121,
        "rx_frequency_range": (400e6, 403e6),  # Hz
        "tx_frequency_range": (430e6, 440e6),  # Hz
        "rx_ant_con": "SMA",
        "tx_ant_con": "SMA",
        "interface": ["RS485", "UART", "I2C", "USB-C"],
    },
    {
        "type": "transceiver",
        "name": "S Band Transceiver - Enduro",
        "data_rate": (0.1, 125),  # kbps
        "modulations": ["FSK", "MSK", "GFSK", "GMSK"],
        "transmit_power_W": (0.4, 2),  # Watts
        "receive_sensitivity_dBm": -121,
        "rx_frequency_range": (2025e6, 2110e6),  # Hz
        "tx_frequency_range": (2200e6, 2290e6),  # Hz
        "rx_ant_con": "SMP",
        "tx_ant_con": "SMP",
        "interface": ["RS-485", "RS-485/422", "USB-C"],
    },
    {
        "type": "transceiver",
        "name": "AX100 - GOMSpace",
        "data_rate": (0.1, 38.4),  # kbps
        "modulations": ["GFSK", "GMSK"],
        "transmit_power_W": 1,  # Watts
        "receive_sensitivity_dBm": -137,
        "rx_frequency_range": (430e6, 440e6),  # Hz
        "tx_frequency_range": (430e6, 440e6),  # Hz
        "rx_ant_con": "MCX",
        "interface": "CSP",
    },
    {
        "type": "transceiver",
        "name": "NanoCom AX2150 - GOMSpace",
        "data_rate": (2.4, 90),  # kbps
        "modulations": ["GFSK", "GMSK"],
        "transmit_power_W": (0.008, 0.5),  # Watts
        "receive_sensitivity_dBm": -113,
        "rx_frequency_range": (2025e6, 2110e6),  # Hz
        "tx_frequency_range": (2200e6, 2290e6),  # Hz
        "rx_ant_con": "SMP",
        "interface": "CSP",
    },
    {
        "type": "transceiver",
        "name": "TOTEM SDR - Alen Space",
        "data_rate": (200, 56000),  # kbps
        "modulations": ["GFSK", "GMSK"],
        "transmit_power_W": (0.1, 3),  # Watts
        "receive_sensitivity_dBm": -89,  # AD9364 transceiver data sheet, assumptions
        "rx_frequency_range": (70e6, 60000e6),  # Hz
        "tx_frequency_range": (70e6, 60000e6),  # Hz
        "rx_ant_con": "MMCX",
        "tx_ant_con": "MMCX",
        "interface": ["UART", "I2C", "JTAG", "ETHERNET", "CAN"],
    },
    {
        "type": "transmitter",
        "name": "S Band Transmitter - Enduro",
        "data_rate": 20000,  # ksps - check data sheet
        "modulations": ["QPSK", "8PSK", "16APSK"],
        "transmit_power_W": (0.5, 2),
        "frequency_range": [(2200e6, 2290e6), (2400e6, 2450e6)],
        "tx_ant_con": "SMA",
        "interface": ["UART", "RS-485", "LVDS"],
    },
    {
        "type": "transmitter",
        "name": "X Band Transmitter - Enduro",
        "data_rate": 150000,  # kbps
        "modulations": ["QPSK", "8PSK", "16APSK", "32APSK"],
        "transmit_power_W": (0.5, 2),
        "frequency_range": [(7900e6, 8400e6)],
        "tx_ant_con": "SMA",
        "interface": ["UART", "RS-485", "LVDS"],
    },
    {
        "type": "transmitter",
        "name": "K Band Transmitter - Enduro",
        "data_rate": 1000000,  # kbps
        "modulations": ["QPSK", "8PSK", "16APSK", "32APSK", "256APSK"],
        "transmit_power_W": (0.5, 2),
        "frequency_range": [(25500e6, 27000e6)],
        "tx_ant_con": "K-connector",
        "interface": ["CAN", "Ethernet", "ESPS-RS-485", "LVDS"],
    },
    {
        "type": "transmitter",
        "name": "XTX X-Band Transmitter - Cubecom",
        "data_rate": (2500, 25000),  # kbps - check symbol rate data sheet
        "modulations": ["QPSK", "8PSK", "16APSK"],
        "transmit_power_W": (0, 2),
        "frequency_range": [(8025e6, 8400e6)],
        "tx_ant_con": "SMP",
        "interface": ["CAN", "I2C", "SpaceWire", "LVDS"],
    },
    {
        "type": "transmitter",
        "name": "HDRTX X-Band Gigabit Transmitter - Cubecom",
        "data_rate": (50000, 200000),  # kbps - check symbol rate data sheet
        "modulations": ["8PSK", "16APSK", "32APSK"],
        "transmit_power_W": (0, 2),
        "frequency_range": [(8025e6, 8400e6)],
        "tx_ant_con": "SMP",
        "interface": ["CAN", "SpaceWire", "8B10B"],
    },
    {
        "type": "transmitter",
        "name": "TX-2400 S-Band Transmitter - AAC",
        "data_rate": (56, 6000),  # kbps
        "modulations": ["FM", "FSK"],
        "transmit_power_W": (1, 10),  # Different models
        "frequency_range": [(2000e6, 2400e6)],
        "tx_ant_con": "SMA",
        "interface": "Micro-D",
    },
]

# Dictionary of TLEs for different orbital lanes
satellite_tles = {
    "LEO": {
        "name": "ISS (ZARYA)",
        "description": "Low Earth Orbit (LEO) satellite - International Space Station.",
        "tle": [
            "1 25544U 98067A   23314.54692130  .00007237  00000-0  13252-3 0  9992",
            "2 25544  51.6425 282.3050 0002927 134.1747  13.9034 15.49925521424794",
        ],
    },
    "MEO": {
        "name": "GPS BIIR-2  (PRN 18)",
        "description": "Medium Earth Orbit (MEO) satellite - Part of the GPS constellation.",
        "tle": [
            "1 24876U 97033A   23314.47420425  .00000025  00000-0  00000-0 0  9997",
            "2 24876  54.8326 305.6921 0152963  58.7624 304.8789  2.00569910172652",
        ],
    },
    "GEO": {
        "name": "GOES-16",
        "description": "Geostationary Orbit (GEO) satellite - Weather monitoring.",
        "tle": [
            "1 41866U 16071A   23314.57030787 -.00000267  00000-0  00000+0 0  9998",
            "2 41866   0.0171 121.1528 0000291 312.5125  47.5398  1.00272067 25134",
        ],
    },
    "Dawn-Dusk Orbit": {
        "name": "Sentinel-2A",
        "description": "Sun-synchronous dawn-dusk orbit satellite for Earth observation.",
        "tle": [
            "1 40697U 15028A   23314.46294037  .00000027  00000-0  23210-4 0  9995",
            "2 40697  98.5672  44.5289 0001275  90.3575 269.7627 14.30883213437250",
        ],
    },
}

# connectors, p dictates precision.
rf_connectors = {
    "SMA": {
        "frequency_range": (0, 18e9),  # Hz
        "impedance": 50,
        "gender": {
            "male": {"contact": "pin", "thread_type": "outer"},
            "female": {"contact": "socket", "thread_type": "inner"},
        },
        "power_handling": "0.5 W (average)",
        "compatible_with": ["3.5 mm", "2.92 mm (K-connector)"],
    },
    "SMA_P": {
        "frequency_range": (0, 26.5e9),  # Hz
        "impedance": 50,
        "gender": {
            "male": {"contact": "pin", "thread_type": "outer"},
            "female": {"contact": "socket", "thread_type": "inner"},
        },
        "power_handling": "0.5 W (average)",
        "compatible_with": ["3.5 mm", "2.92 mm (K-connector)"],
    },
    "N-Type": {
        "frequency_range": (0, 11e9),  # Hz
        "impedance": 50,
        "gender": {
            "male": {"contact": "pin", "thread_type": "outer"},
            "female": {"contact": "socket", "thread_type": "inner"},
        },
        "power_handling": "150 W (average)",
        "compatible_with": ["Weatherproof N-Type"],
    },
    "N-Type_P": {
        "frequency_range": (0, 18e9),  # Hz
        "impedance": 50,
        "gender": {
            "male": {"contact": "pin", "thread_type": "outer"},
            "female": {"contact": "socket", "thread_type": "inner"},
        },
        "power_handling": "150 W (average)",
        "compatible_with": ["Weatherproof N-Type"],
    },
    "Micro-D": {
        "frequency_range": (0, 3e9),  # Hz
        "pins_sockets": {
            "9-pin": {"type": "male/female"},
            "15-pin": {"type": "male/female"},
            "25-pin": {"type": "male/female"},
        },
        "applications": [
            "Aerospace and defense",
            "Satellite communication",
            "High-reliability systems",
        ],
        "mounting": ["Panel mount", "Cable mount"],
        "notes": "Designed for compact, high-reliability connections.",
    },
    "2.92 mm (K-Connector)": {
        "frequency_range": "DC to 40 GHz",
        "impedance": 50,
        "gender": {
            "male": {"contact": "pin", "precision": "high"},
            "female": {"contact": "socket", "precision": "high"},
        },
        "applications": [
            "Precision measurements",
            "High-frequency radar",
            "Satellite payload testing",
        ],
        "compatible_with": ["SMA", "3.5 mm"],
        "notes": "Provides excellent performance at high frequencies and is compatible with SMA and 3.5 mm connectors.",
    },
}

# Ground stations with Skyfield Topos and additional properties
ground_segment = [
    {
        "name": "VIASAT PENDER",
        "network": "VIASAT",
        "location": Topos(
            latitude_degrees=49.1, longitude_degrees=-123.9, elevation_m=30
        ),
        "sup_freq": (2025e6, 2110e6),
        "uEIRP": 53.2,  # dBW
        "sdown_fr": (2200e6, 2290e6),
        "sdown_gt": 17,  # dB/K
        "xdown_fr": (8025e6, 8400e6),
        "xdown_gt": 30,  # dB/K
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "VIASAT GUILDFORD",
        "network": "VIASAT",
        "location": Topos(
            latitude_degrees=51.2, longitude_degrees=-0.6, elevation_m=70
        ),
        "sup_freq": (2025e6, 2110e6),
        "uEIRP": 53.2,
        "sdown_fr": (2200e6, 2290e6),
        "sdown_gt": 17,
        "xdown_fr": (8025e6, 8400e6),
        "xdown_gt": 30,
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "VIASAT ALICE",
        "network": "VIASAT",
        "location": Topos(
            latitude_degrees=-23.7, longitude_degrees=133.9, elevation_m=600
        ),
        "sup_freq": (2025e6, 2110e6),
        "uEIRP": 65.0,
        "sdown_fr": (2200e6, 2290e6),
        "sdown_gt": 18,
        "xdown_fr": (8025e6, 8400e6),
        "xdown_gt": 32,
        "kadown_fr": (25500e6, 27000e6),
        "kadown_gt": 34.5,
    },
    {
        "name": "VIASAT GHANA",
        "network": "VIASAT",
        "location": Topos(
            latitude_degrees=5.6, longitude_degrees=-0.2, elevation_m=50
        ),  # Placeholder coordinates
        "sup_freq": (2025e6, 2110e6),
        "uEIRP": 65.0,
        "sdown_fr": (2200e6, 2290e6),
        "sdown_gt": 18,
        "xdown_fr": (8025e6, 8400e6),
        "xdown_gt": 32,
        "kadown_fr": (25500e6, 27000e6),
        "kadown_gt": 34.5,
    },
    {
        "name": "ATLAS PAUMALU",
        "network": "ATLAS",
        "location": Topos(
            latitude_degrees=21.6, longitude_degrees=-158.0, elevation_m=100
        ),  # Placeholder coordinates
        "sup_freq": (2025e6, 2120e6),
        "uEIRP": 50.0,
        "sdown_fr": (2200e6, 2300e6),
        "sdown_gt": 21,
        "xdown_fr": (7900e6, 8500e6),
        "xdown_gt": 31,
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "AWS Alaska 1",
        "network": "AWS",
        "location": Topos(
            latitude_degrees=64.2008, longitude_degrees=-149.4937, elevation_m=100
        ),  # Placeholder coordinates for Alaska
        "sup_freq": (2025e6, 2110e6),  # S-band uplink
        "uEIRP": 53.0,  # Assumed value based on capabilities
        "sdown_fr": (2200e6, 2290e6),  # S-band downlink
        "sdown_gt": 18,  # Placeholder value
        "xdown_fr": (7750e6, 8400e6),  # X-band downlink
        "xdown_gt": 30,  # Placeholder value
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "AWS Bahrain 1",
        "network": "AWS",
        "location": Topos(
            latitude_degrees=26.0667, longitude_degrees=50.5577, elevation_m=50
        ),  # Placeholder coordinates for Bahrain
        "sup_freq": (2025e6, 2110e6),  # S-band uplink
        "uEIRP": 53.0,  # Assumed value based on capabilities
        "sdown_fr": (2200e6, 2290e6),  # S-band downlink
        "sdown_gt": 18,  # Placeholder value
        "xdown_fr": (7750e6, 8400e6),  # X-band downlink
        "xdown_gt": 30,  # Placeholder value
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "AWS Cape Town 1",
        "network": "AWS",
        "location": Topos(
            latitude_degrees=-33.9249, longitude_degrees=18.4241, elevation_m=50
        ),  # Placeholder coordinates for Cape Town
        "sup_freq": (2025e6, 2110e6),  # S-band uplink
        "uEIRP": 53.0,  # Assumed value based on capabilities
        "sdown_fr": (2200e6, 2290e6),  # S-band downlink
        "sdown_gt": 18,  # Placeholder value
        "xdown_fr": (7750e6, 8400e6),  # X-band downlink
        "xdown_gt": 30,  # Placeholder value
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "AWS Dubbo 1",
        "network": "AWS",
        "location": Topos(
            latitude_degrees=-32.2569, longitude_degrees=148.6011, elevation_m=50
        ),  # Placeholder coordinates for Dubbo
        "sup_freq": (2025e6, 2110e6),  # S-band uplink
        "uEIRP": 53.0,  # Assumed value based on capabilities
        "sdown_fr": (2200e6, 2290e6),  # S-band downlink
        "sdown_gt": 18,  # Placeholder value
        "xdown_fr": (7750e6, 8400e6),  # X-band downlink
        "xdown_gt": 30,  # Placeholder value
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "AWS Hawaii 1",
        "network": "AWS",
        "location": Topos(
            latitude_degrees=19.8968, longitude_degrees=-155.5828, elevation_m=100
        ),  # Placeholder coordinates for Hawaii
        "sup_freq": (2025e6, 2110e6),  # S-band uplink
        "uEIRP": 53.0,  # Assumed value based on capabilities
        "sdown_fr": (2200e6, 2290e6),  # S-band downlink
        "sdown_gt": 18,  # Placeholder value
        "xdown_fr": (7750e6, 8400e6),  # X-band downlink
        "xdown_gt": 30,  # Placeholder value
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "AWS Ireland 1",
        "network": "AWS",
        "location": Topos(
            latitude_degrees=53.1424, longitude_degrees=-7.6921, elevation_m=50
        ),  # Placeholder coordinates for Ireland
        "sup_freq": (2025e6, 2110e6),  # S-band uplink
        "uEIRP": 53.0,
        "sdown_fr": (2200e6, 2290e6),
        "sdown_gt": 18,
        "xdown_fr": (7750e6, 8400e6),
        "xdown_gt": 30,
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "AWS Ohio 1",
        "network": "AWS",
        "location": Topos(
            latitude_degrees=40.4173, longitude_degrees=-82.9071, elevation_m=50
        ),  # Placeholder coordinates for Ohio
        "sup_freq": (2025e6, 2110e6),  # S-band uplink
        "uEIRP": 53.0,
        "sdown_fr": (2200e6, 2290e6),
        "sdown_gt": 18,
        "xdown_fr": (7750e6, 8400e6),
        "xdown_gt": 30,
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "AWS Oregon 1",
        "network": "AWS",
        "location": Topos(
            latitude_degrees=43.8041, longitude_degrees=-120.5542, elevation_m=100
        ),  # Placeholder coordinates for Oregon
        "sup_freq": (2025e6, 2110e6),  # S-band uplink
        "uEIRP": 53.0,
        "sdown_fr": (2200e6, 2290e6),
        "sdown_gt": 18,
        "xdown_fr": (7750e6, 8400e6),
        "xdown_gt": 30,
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "AWS Punta Arenas 1",
        "network": "AWS",
        "location": Topos(
            latitude_degrees=-53.1638, longitude_degrees=-70.9171, elevation_m=50
        ),  # Placeholder coordinates for Punta Arenas
        "sup_freq": (2025e6, 2110e6),  # S-band uplink
        "uEIRP": 53.0,
        "sdown_fr": (2200e6, 2290e6),
        "sdown_gt": 18,
        "xdown_fr": (7750e6, 8400e6),
        "xdown_gt": 30,
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "AWS Seoul 1",
        "network": "AWS",
        "location": Topos(
            latitude_degrees=37.5665, longitude_degrees=126.9780, elevation_m=50
        ),  # Placeholder coordinates for Seoul
        "sup_freq": (2025e6, 2110e6),  # S-band uplink
        "uEIRP": 53.0,
        "sdown_fr": (2200e6, 2290e6),
        "sdown_gt": 18,
        "xdown_fr": (7750e6, 8400e6),
        "xdown_gt": 30,
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "AWS Singapore 1",
        "network": "AWS",
        "location": Topos(
            latitude_degrees=1.3521, longitude_degrees=103.8198, elevation_m=50
        ),  # Placeholder coordinates for Singapore
        "sup_freq": (2025e6, 2110e6),  # S-band uplink
        "uEIRP": 53.0,
        "sdown_fr": (2200e6, 2290e6),
        "sdown_gt": 18,
        "xdown_fr": (7750e6, 8400e6),
        "xdown_gt": 30,
        "kadown_fr": None,
        "kadown_gt": None,
    },
    {
        "name": "AWS Stockholm 1",
        "network": "AWS",
        "location": Topos(
            latitude_degrees=59.3293, longitude_degrees=18.0686, elevation_m=50
        ),  # Placeholder coordinates for Stockholm
        "sup_freq": (2025e6, 2110e6),  # S-band uplink
        "uEIRP": 53.0,
        "sdown_fr": (2200e6, 2290e6),
        "sdown_gt": 18,
        "xdown_fr": (7750e6, 8400e6),
        "xdown_gt": 30,
        "kadown_fr": None,
        "kadown_gt": None,
    },
]

# Map networks to their ground stations for easy filtering
ground_stations_by_network = {}
for gs in ground_segment:
    ground_stations_by_network.setdefault(gs["network"], []).append(gs)

# ... [Your big antennas, modems_sdrs, ground_segment dictionaries go here, unchanged] ...
# If you omitted them for brevity, add them back above this function.

c = 3e8
k = 1.38e-23


def calculate_fspl(distance_m, frequency_hz):
    return 20 * np.log10((4 * np.pi * distance_m * frequency_hz) / c)


def compute_BER(Eb_N0_dB, modulation):
    Eb_N0 = 10 ** (Eb_N0_dB / 10)
    if modulation in ["BPSK", "OOK", "GMSK", "GFSK", "FSK", "MSK"]:
        return 0.5 * erfc(np.sqrt(Eb_N0))
    elif modulation == "QPSK":
        return 0.5 * erfc(np.sqrt(Eb_N0))
    elif modulation == "8PSK":
        return erfc(np.sqrt(1.5 * Eb_N0 * np.log2(8) / (8 - 1)))
    elif modulation in ["16QAM", "16APSK"]:
        return (3 / 8) * erfc(np.sqrt((4 / 5) * Eb_N0))
    elif modulation == "32APSK":
        return erfc(np.sqrt(0.068 * Eb_N0))
    elif modulation == "256APSK":
        return erfc(np.sqrt(0.0156 * Eb_N0))
    else:
        return 1.0


def select_antennas_for_freq(freq_hz):
    return [
        ant
        for ant in antennas
        if ant["frequency_range"][0] <= freq_hz <= ant["frequency_range"][1]
    ]


def select_modems_for_freq_and_type(freq_hz, mtype="transmitter"):
    hits = []
    for modem in modems_sdrs:
        if mtype in modem["type"]:
            key = (
                "tx_frequency_range" if mtype == "transmitter" else "rx_frequency_range"
            )
            frange = modem.get(key) or modem.get("frequency_range")
            if not frange:
                continue
            if isinstance(frange, list):
                match = any(
                    fr[0] <= freq_hz <= fr[1] for fr in frange if isinstance(fr, tuple)
                )
            else:
                if isinstance(frange, tuple):
                    match = frange[0] <= freq_hz <= frange[1]
                else:
                    match = False
            if match:
                hits.append(modem)
    return hits


def calc_link_budget(
    distance_m,
    freq_hz,
    tx_power_W,
    tx_gain_dBi,
    rx_gain_dBi,
    data_rate_bps,
    modulation,
    T_sys=290,
    BER_thresh=1e-5,
):
    bits_per_symbol = modulation_bits_per_symbol.get(modulation, 1)
    fspl_dB = calculate_fspl(distance_m, freq_hz)
    P_tx_dBm = 10 * np.log10(tx_power_W * 1e3)
    P_rx_dBm = P_tx_dBm + tx_gain_dBi + rx_gain_dBi - fspl_dB
    bandwidth_Hz = data_rate_bps / bits_per_symbol
    P_noise_dBm = 10 * np.log10(k * T_sys * bandwidth_Hz) + 30
    SNR_dB = P_rx_dBm - P_noise_dBm
    Eb_N0_dB = SNR_dB - 10 * np.log10(bits_per_symbol)
    BER = compute_BER(Eb_N0_dB, modulation)
    link_margin_dB = SNR_dB - (10 * np.log10(bits_per_symbol) + BER_thresh)
    return {
        "P_rx_dBm": P_rx_dBm,
        "SNR_dB": SNR_dB,
        "Eb_N0_dB": Eb_N0_dB,
        "BER": BER,
        "link_margin_dB": link_margin_dB,
    }


def full_rf_visibility_simulation(
    tle=None,
    uplink_bps=5000,
    downlink_bps=10000,
    duration_days=30,
    verbose=True,
    print_results=None,
    networks=None,
):
    if print_results is not None:
        verbose = print_results
    if tle is None:
        tle = [
            "1 25544U 98067A   23314.54692130  .00007237  00000-0  13252-3 0  9992",
            "2 25544  51.6425 282.3050 0002927 134.1747  13.9034 15.49925521424794",
        ]
    ts = load.timescale()
    start_time = datetime.datetime.utcnow()
    end_time = start_time + datetime.timedelta(days=duration_days)
    t0 = ts.utc(start_time.year, start_time.month, start_time.day)
    t1 = ts.utc(end_time.year, end_time.month, end_time.day)
    sat = EarthSatellite(tle[0], tle[1], "user_sat", ts)

    total_data_down = 0.0
    total_data_up = 0.0
    total_downlink_contact_s = 0.0
    total_uplink_contact_s = 0.0
    passes_analyzed = 0
    best_down_margin_dB = None
    best_up_margin_dB = None
    min_pass_duration = 60

    T_sys_gs = 290
    T_sys_sat = 290
    BER_thresh_dn = 1e-5
    BER_thresh_up = 1e-7
    mission_s = duration_days * 24 * 3600

    if networks:
        if isinstance(networks, str):
            networks = [networks]
        gs_list = [g for g in ground_segment if g["network"] in networks]
    else:
        gs_list = ground_segment

    for gs in gs_list:
        gloc = gs["location"]
        t_events, events = sat.find_events(gloc, t0, t1, altitude_degrees=10.0)
        passes = []
        cur = {}
        for ti, event in zip(t_events, events):
            if event == 0:
                cur = {"start": ti}
            elif event == 2:
                cur["end"] = ti
                if "start" in cur:
                    passes.append(cur)
                cur = {}
        for p in passes:
            pass_dur = (
                p["end"].utc_datetime() - p["start"].utc_datetime()
            ).total_seconds()
            if pass_dur < min_pass_duration:
                continue
            passes_analyzed += 1
            mid_time = (
                p["start"].utc_datetime()
                + (p["end"].utc_datetime() - p["start"].utc_datetime()) / 2
            )
            mid_ts = ts.utc(mid_time)
            diff = sat - gloc
            topoc = diff.at(mid_ts)
            dist_m = topoc.distance().m

            # ---- Downlink ----
            dn_bands = [
                ("sdown_fr", gs.get("sdown_fr"), gs.get("sdown_gt")),
                ("xdown_fr", gs.get("xdown_fr"), gs.get("xdown_gt")),
                ("kadown_fr", gs.get("kadown_fr"), gs.get("kadown_gt")),
            ]
            best_down = None
            for band, frange, gt in dn_bands:
                if not frange:
                    continue
                midf = (frange[0] + frange[1]) / 2
                tx_modems = select_modems_for_freq_and_type(midf, "transmitter")
                for m in tx_modems:
                    tx_power = 2
                    if isinstance(m.get("transmit_power_W"), (list, tuple)):
                        tx_power = max(m["transmit_power_W"])
                    elif isinstance(m.get("transmit_power_W"), (int, float)):
                        tx_power = m["transmit_power_W"]
                    for mod in m.get("modulations", []):
                        bits_per_symbol = modulation_bits_per_symbol.get(mod, 1)
                        ant_list = select_antennas_for_freq(midf)
                        if not ant_list:
                            continue
                        ant = max(ant_list, key=lambda a: a["gain"])
                        lb = calc_link_budget(
                            dist_m,
                            midf,
                            tx_power,
                            ant["gain"],
                            gt,
                            downlink_bps,
                            mod,
                            T_sys_gs,
                            BER_thresh_dn,
                        )
                        if (
                            best_down is None
                            or lb["link_margin_dB"] > best_down["lb"]["link_margin_dB"]
                        ):
                            best_down = {
                                "modem": m,
                                "ant": ant,
                                "lb": lb,
                                "mod": mod,
                                "gs": gs,
                                "band": band,
                                "midf": midf,
                            }
            if best_down and best_down["lb"]["link_margin_dB"] > 0:
                total_data_down += downlink_bps * pass_dur
                total_downlink_contact_s += pass_dur
                margin = best_down["lb"]["link_margin_dB"]
                if best_down_margin_dB is None or margin > best_down_margin_dB:
                    best_down_margin_dB = margin
                if verbose:
                    print(
                        f"\n[DOWNLINK] GS={gs['name']}, F={best_down['midf']/1e6:.1f} MHz, Ant={best_down['ant']['name']} ({best_down['ant']['gain']} dBi), Dev={best_down['modem']['name']}, Mod={best_down['mod']}"
                    )
                    print(
                        f"  Pass {passes_analyzed}: {pass_dur:.1f}s, SNR={best_down['lb']['SNR_dB']:.2f} dB, Margin={best_down['lb']['link_margin_dB']:.2f}, BER={best_down['lb']['BER']:.2e} [LINK OK]"
                    )

            # ---- Uplink ----
            up_frange = gs.get("sup_freq")
            if up_frange:
                midf = (up_frange[0] + up_frange[1]) / 2
                rx_modems = select_modems_for_freq_and_type(midf, "receiver")
                for m in rx_modems:
                    gs_eirp_W = 50
                    ant_list = select_antennas_for_freq(midf)
                    if not ant_list:
                        continue
                    ant = max(ant_list, key=lambda a: a["gain"])
                    for mod in m.get("modulations", []):
                        lb = calc_link_budget(
                            dist_m,
                            midf,
                            gs_eirp_W,
                            20,
                            ant["gain"],
                            uplink_bps,
                            mod,
                            T_sys_sat,
                            BER_thresh_up,
                        )
                        if lb["link_margin_dB"] > 0:
                            total_data_up += uplink_bps * pass_dur
                            total_uplink_contact_s += pass_dur
                            margin_up = lb["link_margin_dB"]
                            if (
                                best_up_margin_dB is None
                                or margin_up > best_up_margin_dB
                            ):
                                best_up_margin_dB = margin_up
                            if verbose:
                                print(
                                    f"[UPLINK] GS={gs['name']}, F={midf/1e6:.1f} MHz, Ant={ant['name']} ({ant['gain']} dBi), Dev={m['name']}, Mod={mod}"
                                )
                                print(
                                    f"  Pass {passes_analyzed}: {pass_dur:.1f}s, SNR={lb['SNR_dB']:.2f} dB, Margin={lb['link_margin_dB']:.2f}, BER={lb['BER']:.2e} [LINK OK]"
                                )

    # --- Return results as rf_dict ---
    rf_dict = {
        "Total passes analyzed": passes_analyzed,
        "Total downlink data (GB)": f"{total_data_down / 8 / 1e9:.2f}",
        "Total uplink data (GB)": f"{total_data_up / 8 / 1e9:.2f}",
        "Total downlink contact time (hr)": f"{total_downlink_contact_s / 3600:.2f}",
        "Total uplink contact time (hr)": f"{total_uplink_contact_s / 3600:.2f}",
        "Downlink % of mission": f"{100*total_downlink_contact_s/mission_s:.2f}%",
        "Uplink % of mission": f"{100*total_uplink_contact_s/mission_s:.2f}%",
    }

    if best_down_margin_dB is not None:
        rf_dict["Best downlink margin (dB)"] = float(f"{best_down_margin_dB:.2f}")
    if best_up_margin_dB is not None:
        rf_dict["Best uplink margin (dB)"] = float(f"{best_up_margin_dB:.2f}")

    if verbose:
        print(f"\n--- RF Analysis Complete ---")
        print(f"Total passes analyzed: {passes_analyzed}")
        print(f"Total downlink data (GB): {total_data_down/8/1e9:.2f}")
        print(f"Total uplink data (GB): {total_data_up/8/1e9:.2f}")
        print(
            f"Total downlink contact time: {total_downlink_contact_s/3600:.2f} hr ({100*total_downlink_contact_s/mission_s:.2f}% of mission)"
        )
        print(
            f"Total uplink contact time: {total_uplink_contact_s/3600:.2f} hr ({100*total_uplink_contact_s/mission_s:.2f}% of mission)"
        )

    return rf_dict


def rf_margin_timeseries(
    tle,
    networks=None,
    dt=60,
    downlink_bps=10000,
    verbose=False,
):
    """Return times (s) and best downlink margin (dB) over one orbit."""
    ts = load.timescale()
    sat = EarthSatellite(tle[0], tle[1], "user_sat", ts)
    period_min = 2 * np.pi / sat.model.no_kozai
    period_s = period_min * 60

    if networks:
        if isinstance(networks, str):
            networks = [networks]
        gs_list = [g for g in ground_segment if g["network"] in networks]
    else:
        gs_list = ground_segment

    T_sys_gs = 290
    BER_thresh_dn = 1e-5

    start = datetime.datetime.utcnow()
    n_steps = int(period_s // dt) + 1
    times = []
    margins = []

    for i in range(n_steps):
        t = start + datetime.timedelta(seconds=i * dt)
        ts_t = ts.utc(
            t.year,
            t.month,
            t.day,
            t.hour,
            t.minute,
            t.second + t.microsecond / 1e6,
        )
        best_margin = None
        for gs in gs_list:
            diff = sat - gs["location"]
            topoc = diff.at(ts_t)
            alt = topoc.altaz()[0].degrees
            if alt < 10:
                continue
            dist_m = topoc.distance().m
            dn_bands = [
                ("sdown_fr", gs.get("sdown_fr"), gs.get("sdown_gt")),
                ("xdown_fr", gs.get("xdown_fr"), gs.get("xdown_gt")),
                ("kadown_fr", gs.get("kadown_fr"), gs.get("kadown_gt")),
            ]
            for _band, frange, gt in dn_bands:
                if not frange:
                    continue
                midf = (frange[0] + frange[1]) / 2
                ant_list = select_antennas_for_freq(midf)
                if not ant_list:
                    continue
                ant = max(ant_list, key=lambda a: a["gain"])
                tx_modems = select_modems_for_freq_and_type(midf, "transmitter")
                tx_pwr = 2
                for m in tx_modems:
                    if isinstance(m.get("transmit_power_W"), (list, tuple)):
                        tx_pwr = max(m["transmit_power_W"])
                    elif isinstance(m.get("transmit_power_W"), (int, float)):
                        tx_pwr = m["transmit_power_W"]
                    for mod in m.get("modulations", []):
                        lb = calc_link_budget(
                            dist_m,
                            midf,
                            tx_pwr,
                            ant["gain"],
                            gt,
                            downlink_bps,
                            mod,
                            T_sys_gs,
                            BER_thresh_dn,
                        )
                        margin = lb["link_margin_dB"]
                        if best_margin is None or margin > best_margin:
                            best_margin = margin

        times.append(i * dt)
        margins.append(best_margin if best_margin is not None else float("nan"))

    return times, margins


def rf_margin_plot_to_buffer(tle, networks=None, dt=60, verbose=False):
    """Return an RF margin plot for one orbit."""
    times, margins = rf_margin_timeseries(
        tle, networks=networks, dt=dt, verbose=verbose
    )
    hours = np.array(times) / 3600.0
    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
    ax.plot(hours, margins)
    ax.set_xlabel("Time (hr)")
    ax.set_ylabel("Downlink Margin (dB)")
    ax.set_title("RF Margin Over One Orbit")
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def constant_margin_plot_to_buffer(margin_dB=5.0, period_s=5400, dt=60):
    """Return a simple plot with constant margin over one orbit.

    Parameters
    ----------
    margin_dB : float, optional
        Fixed link margin to display. Defaults to ``5`` dB which indicates
        a reliable relay link.
    period_s : float, optional
        Orbit period in seconds.
    dt : int, optional
        Time step between points.
    """
    times = np.arange(0, period_s + dt, dt)
    margins = np.full_like(times, margin_dB, dtype=float)
    hours = times / 3600.0
    fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
    ax.plot(hours, margins)
    ax.set_xlabel("Time (hr)")
    ax.set_ylabel("Downlink Margin (dB)")
    ax.set_title("RF Margin Over One Orbit")
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


# This allows calling directly
if __name__ == "__main__":
    full_rf_visibility_simulation(print_results=True)
