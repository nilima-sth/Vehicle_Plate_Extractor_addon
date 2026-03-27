{
    "name": "Vehicle Plate Extractor",
    "version": "19.0.1.0.0",
    "category": "Plate extractor",
    "sequence": -100,
    "summary": "Extracts license plate information from vehicle records",
    "depends": ["base"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "data/hide_fleet_menus.xml",
        "security/ir.model.access.csv",
        "views/vehicle_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
