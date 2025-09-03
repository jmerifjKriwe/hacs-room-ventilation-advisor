"""Setup for Room Ventilation Advisor."""

from setuptools import setup

setup(
    name="room-ventilation-advisor",
    version="0.0.0",
    description="Room Ventilation Advisor for Home Assistant",
    author="jmerifjKriwe",
    packages=["custom_components.room_ventilation_advisor"],
    package_dir={
        "custom_components.room_ventilation_advisor": (
            "custom_components/room_ventilation_advisor"
        ),
    },
    include_package_data=True,
    zip_safe=False,
)
