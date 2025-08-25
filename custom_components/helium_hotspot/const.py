DOMAIN = "helium_hotspot"

CONF_HOTSPOTS = "hotspots"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"

DEFAULT_UPDATE_INTERVAL_MINUTES = 60  # 1 hour
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# sensor keys => (name, unit_of_measurement)
SENSOR_TYPES = {
    "tokens_earned_30d_hnt": ("HNT (30D)", "HNT"),
    "proof_of_coverage_30d": ("PoC (30D)", "HNT"),
    "data_transfer_30d": ("Data Transfer (30D HNT)", "HNT"),
    "carrier_offload": ("Carrier Offload (30D)", None),
    "helium_mobile": ("Helium Mobile (30D)", None),
    "avg_daily_data": ("Avg Daily Data", None),
    "avg_daily_users": ("Avg Daily Users", None),
}
