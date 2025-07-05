# SF3 Blender Addon
This is a repository that contains an addon for Blender to support importing and exporting [Simple File Format Family (SF3)](https://shirakumo.org/docs/sf3) models.

## Installation
You can [download the latest release](https://github.com/Shirakumo/sf3-blender-addon/releases/latest/) of the plugin. The zip file can be imported into Blender just like any other addon.

Activating the ``SHIRAKUMO_sf3_io`` addon should give you new menu entries under ``File > Import`` and ``File > Export`` for importing/exporting SF3 model files.

## Feature Support
Supports importing and exporting of the following:

- SF3 Model files (``.mod.sf3``)
  For single mesh and material storage
- SF3 Image files (``.img.sf3``)
  For texture storage
- SF3 Archive files (``.ar.sf3``)
  To bundle multiple meshes and materials together
