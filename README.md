# Bos-FBX-Importer-Exporter
Bos FBX Importer/Exporter for Blender (Win64 only)  

Working release is 2.79.

Current master is not working.  I posted it here for someone who instrested to work on it for Blender 2.80.

\_\_init\_\_.py is updated, except the property.  As a result, the warning message "contains a property which should be an annotation!" will be shown in the console.

export_bos_fbx.py is modified to perform export.  It seems to work.  
Noted that the lines 405 and 406 are commented:

        #fbx_material.set_emissive(to_umvec(material.mirror_color))
        #fbx_material.set_transparency_factor(material.alpha)

As the result, the materials are not exported properly.

import_bos_fbx.py is broken.  Use the 2.79 version as a reference.
