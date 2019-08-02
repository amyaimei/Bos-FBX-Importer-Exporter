# author: tori31001 at gmail.com
# website: http://blenderfbx.render.jp/
import bpy
import os
import sys
import math
import mathutils
import platform
import imp
import tempfile
from bpy_extras.io_utils import unpack_list, unpack_face_list

def to_umvec(src):
    import UMIO
    v = UMIO.UMVec4d()
    v.x = src[0]
    v.y = src[1]
    v.z = src[2]
    if len(src) > 3:
        v.w = src[3]
    return v

def export_skeleton_chain(obj, armature_object, exported_bone_list, parent_id, pbone, pbone_to_props, fit_node_length):
    SWAP_YZ_MATRIX = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
    ROT_Z90 = mathutils.Matrix.Rotation( math.pi/2.0, 4, 'Z')

    import UMIO
    skeleton = UMIO.UMSkeleton()
    skeleton.set_name(str(pbone.name))
    skeleton.set_type(UMIO.UMSkeleton.SkeletonType.Limb)
    skeleton.set_size(1.0)
    matrix = pbone.bone.matrix_local.copy()
    if pbone.parent == None:
        matrix = (SWAP_YZ_MATRIX * armature_object.matrix_basis).inverted() * matrix * ROT_Z90
    else:
        matrix = (pbone.parent.bone.matrix_local.copy() * ROT_Z90).inverted() * matrix * ROT_Z90
        
    trans, rot, scale = matrix.decompose()
        
    rad = rot.normalized().to_euler() 
    to_degree = 180 / math.pi
    rot = mathutils.Vector([ rad[0] * to_degree, rad[1] * to_degree, rad[2] * to_degree])

    if pbone in pbone_to_props:
        properties = pbone_to_props[pbone]
        t = properties[0]
        r = properties[1]
        s = properties[2]
        if t != None:
            trans = t
        if r != None:
            rot = r
        if s != None:
            scale = s
            
        if properties[3] != None:
            skeleton.set_rotation_offset(properties[3])
        if properties[4] != None:
            skeleton.set_rotation_pivot(properties[4])
        if properties[5] != None:
            skeleton.set_pre_rotation(properties[5])
        if properties[6] != None:
            skeleton.set_post_rotation(properties[6])
        if properties[7] != None:
            skeleton.set_scaling_offset(properties[7])
        if properties[8] != None:
            skeleton.set_scaling_pivot(properties[8])
        if properties[9] != None:
            skeleton.set_geometric_translation(properties[9])
        if properties[10] != None:
            skeleton.set_geometric_rotation(properties[10])
        if properties[11] != None:
            skeleton.set_geometric_scaling(properties[11])
    
    t = mathutils.Vector([trans[0], trans[1], trans[2]])
    if pbone.parent and fit_node_length:
        if pbone.parent.length > 0.1:
            if t.length > 0:
                s = pbone.parent.length / t.length
                #print (pbone.parent.length, t.length)
                trans = t * s
    #print(t.normalized(), pbone.length)
            
    skeleton.set_local_translation(to_umvec([trans[0], trans[1], trans[2]]))
    skeleton.set_local_rotation(to_umvec([rot[0], rot[1], rot[2]]))
    
    #scale[0] = s
    #scale[1] = s
    #scale[2] = s
    #print(scale)
    
    skeleton.set_local_scaling(to_umvec([scale[0], scale[1], scale[2]]))
    skeleton.set_limb_length(pbone.length)
    
    skeleton.set_parent_id(int(parent_id))
    exported_bone_list.append(pbone)
    node_id = len(exported_bone_list)
    skeleton.set_id(int(node_id))
  
    obj.add_skeleton(skeleton)

    for child in pbone.children:
        export_skeleton_chain(obj, armature_object, exported_bone_list, node_id, child, pbone_to_props, fit_node_length)

def get_fbx_property_dict(armature_object, context):
    armature_object.select = True
    context.scene.objects.active = armature_object
    
    # ebone index to ([tx,ty,tz],[rx,ry,rz],[sx,sy,sz]) or (None,..)
    index_to_properties= {}
        
    # get fbx property if exists
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    ebones = armature_object.data.edit_bones
    for i, ebone in enumerate(ebones):
        
        has_trans = False
        has_rot = False
        has_scale = False
        
        trans = [0,0,0]
        rot = [0,0,0]
        scale = [1,1,1]
        
        if hasattr(ebone, "fbx_local_translation_x"):
            has_trans = True
            trans[0] = ebone.fbx_local_translation_x
        if hasattr(ebone, "fbx_local_translation_y"):
            has_trans = True
            trans[1] = ebone.fbx_local_translation_y
        if hasattr(ebone, "fbx_local_translation_z"):
            has_trans= True
            trans[2] = ebone.fbx_local_translation_z
            
        if hasattr(ebone, "fbx_local_rotation_x"):
            has_rot = True
            rot[0] = ebone.fbx_local_rotation_x
        if hasattr(ebone, "fbx_local_rotation_y"):
            has_rot = True
            rot[1] = ebone.fbx_local_rotation_y
        if hasattr(ebone, "fbx_local_rotation_z"):
            has_rot = True
            rot[2] = ebone.fbx_local_rotation_z
            
        if hasattr(ebone, "fbx_local_scaling_x"):
            has_scale = True
            scale[0] = ebone.fbx_local_scaling_x
        if hasattr(ebone, "fbx_local_scaling_y"):
            has_scale = True
            scale[1] = ebone.fbx_local_scaling_y
        if hasattr(ebone, "fbx_local_scaling_z"):
            has_scale = True
            scale[2] = ebone.fbx_local_scaling_z
        
        if not has_trans:
            trans = None
        if not has_rot:
            rot = None
        if not has_scale:
            scale = None

        properties = (trans,rot,scale)
        
        if hasattr(ebone, "fbx_rotation_offset"):
            x,y,z = ebone.fbx_rotation_offset
            properties = properties + ([x,y,z,1],)
        else:
            properties = properties + (None,)

        if hasattr(ebone, "fbx_rotation_pivot"):
            x,y,z = ebone.fbx_rotation_pivot
            properties = properties + ([x,y,z,1],)
        else:
            properties = properties + (None,)

        if hasattr(ebone, "fbx_pre_rotation"):
            x,y,z = ebone.fbx_pre_rotation
            properties = properties + ([x,y,z,1],)
        else:
            properties = properties + (None,)
            
        if hasattr(ebone, "fbx_post_rotation"):
            x,y,z = ebone.fbx_post_rotation
            properties = properties + ([x,y,z,1],)
        else:
            properties = properties + (None,)
            
        if hasattr(ebone, "fbx_scaling_offset"):
            x,y,z = ebone.fbx_scaling_offset
            properties = properties + ([x,y,z,1],)
        else:
            properties = properties + (None,)
            
        if hasattr(ebone, "fbx_scaling_pivot"):
            x,y,z = ebone.fbx_scaling_pivot
            properties = properties + ([x,y,z,1],)
        else:
            properties = properties + (None,)
            
        if hasattr(ebone, "fbx_geometric_translation"):
            x,y,z = ebone.fbx_geometric_translation
            properties = properties + ([x,y,z,1],)
        else:
            properties = properties + (None,)
            
        if hasattr(ebone, "fbx_geometric_rotation"):
            x,y,z = ebone.fbx_geometric_rotation
            properties = properties + ([x,y,z,1],)
        else:
            properties = properties + (None,)
            
        if hasattr(ebone, "fbx_geometric_scaling"):
            x,y,z = ebone.fbx_geometric_scaling
            properties = properties + ([x,y,z,1],)
        else:
            properties = properties + (None,)
            
        index_to_properties[i] = properties
        
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    return index_to_properties
    
def export_armature(obj, armature_object, context, imported_node_property, fit_node_length):
    if armature_object == None or armature_object.pose == None:
        return

    bpy.types.EditBone.fbx_local_translation_x = bpy.props.FloatProperty()
    bpy.types.EditBone.fbx_local_translation_y = bpy.props.FloatProperty()
    bpy.types.EditBone.fbx_local_translation_z = bpy.props.FloatProperty()
    bpy.types.EditBone.fbx_local_rotation_x = bpy.props.FloatProperty()
    bpy.types.EditBone.fbx_local_rotation_y = bpy.props.FloatProperty()
    bpy.types.EditBone.fbx_local_rotation_z = bpy.props.FloatProperty()
    bpy.types.EditBone.fbx_local_scaling_x = bpy.props.FloatProperty()
    bpy.types.EditBone.fbx_local_scaling_y = bpy.props.FloatProperty()
    bpy.types.EditBone.fbx_local_scaling_z = bpy.props.FloatProperty()
    
    bpy.types.EditBone.fbx_rotation_offset = bpy.props.FloatVectorProperty()
    bpy.types.EditBone.fbx_rotation_pivot = bpy.props.FloatVectorProperty()
    bpy.types.EditBone.fbx_pre_rotation = bpy.props.FloatVectorProperty()
    bpy.types.EditBone.fbx_post_rotation = bpy.props.FloatVectorProperty()
    bpy.types.EditBone.fbx_scaling_offset = bpy.props.FloatVectorProperty()
    bpy.types.EditBone.fbx_scaling_pivot = bpy.props.FloatVectorProperty()
    bpy.types.EditBone.fbx_geometric_translation = bpy.props.FloatVectorProperty()
    bpy.types.EditBone.fbx_geometric_rotation = bpy.props.FloatVectorProperty()
    bpy.types.EditBone.fbx_geometric_scaling = bpy.props.FloatVectorProperty()
    
    index_to_props = get_fbx_property_dict(armature_object, context)
    
    pbones = armature_object.pose.bones
    if pbones == None:
        return None

    pbone_to_props = {}
    root_pbones = []
    for i, pbone in enumerate(pbones):
        if i in index_to_props:
            pbone_to_props[pbone] = index_to_props[i]
            
        if pbone.parent == None:
            root_pbones.append(pbone)
    
    if len(root_pbones) == 0:
        return

    if not imported_node_property:
        pbone_to_props = {}
    
    exported_bone_list = []
    for i, root_pbone in enumerate(root_pbones):
        export_skeleton_chain(obj, armature_object, exported_bone_list, len(exported_bone_list), root_pbone, pbone_to_props, fit_node_length)

def export_skin(obj, fbx_mesh, mesh_object, context):
    import UMIO

    mesh = mesh_object.data
    basis_mesh = mesh #BPyMesh.getMeshFromObject(mesh_object, None, True, True, self.scene)

    link_skeleton_ids = {}
    normalize_values = {}
    for n, vertex in enumerate(basis_mesh.vertices):
        for vertex_group in vertex.groups:
            group_name = mesh_object.vertex_groups[vertex_group.group].name
            link_id = -1
            for skeleton_ in obj.skeleton_list():
                skeleton = skeleton_.data()
                if skeleton.name() == group_name:
                    link_id = skeleton.id()
                    link_skeleton_ids[group_name] = link_id
            if link_id < 0:
                continue
            
            if not (vertex.index in normalize_values):
                normalize_values[vertex.index] = 0.0
            normalize_values[vertex.index] = normalize_values[vertex.index] + vertex_group.weight

    skin = UMIO.UMSkin()
    skin.set_name(mesh_object.name + "_skin")
    
    cluster_dict = {}
    for n, vertex in enumerate(basis_mesh.vertices):
        for vertex_group in vertex.groups:
            group_name = mesh_object.vertex_groups[vertex_group.group].name    
            if not (group_name in link_skeleton_ids):
                continue
            
            link_id = link_skeleton_ids[group_name]
            
            cluster = None
            if not (group_name in cluster_dict):
                cluster = UMIO.UMCluster()
                cluster.set_name(group_name+"_cluster")
                cluster.set_link_mode(UMIO.UMCluster.Normalize)
                cluster.set_link_node_id(link_id)
                cluster_dict[group_name] = cluster
            else:
                cluster = cluster_dict[group_name]
                
            cluster.add_index(vertex.index)
            if normalize_values[vertex.index] > 0:
                cluster.add_weight(vertex_group.weight / normalize_values[vertex.index])
            else:
                cluster.add_weight(vertex_group.weight)
    
    for cluster in cluster_dict.values():
        #print('index', len(cluster.index_list()))
        #print('weight', len(cluster.weight_list()))
        skin.add_cluster(cluster)
        
    fbx_mesh.add_skin(skin)

def export_shape_key(obj, fbx_mesh, mesh_object, context):
    mesh = mesh_object.data
    basis_mesh = mesh
    
    import UMIO

    SWAP_YZ_MATRIX = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
    mesh_rot = mesh_object.matrix_basis.to_quaternion().to_matrix().inverted()
    if mesh.shape_keys != None:
        UMend_shape = UMIO.UMBlendShape()
        blend_shape.set_name(mesh.shape_keys.name)
        for shape in mesh.shape_keys.key_blocks:
            if shape == mesh.shape_keys.reference_key:
                continue
            
            channel = UMIO.UMBlendShapeChannel()
            channel.set_deform_percent(0.0)
            
            target_shape = UMIO.UMShape()
            target_shape.set_name(shape.name)
            target_shape.set_base_geometry_node_id(fbx_mesh.id())
            for data in shape.data:
                target_shape.add_vertex(SWAP_YZ_MATRIX.inverted() * data.co * mesh_rot)
                            
            channel.add_target_shape(target_shape)
            blend_shape.add_blend_shape_channel(channel)
        
        fbx_mesh.add_blend_shape(blend_shape)

def export_mesh(obj, mesh_object, context):
    if mesh_object == None:
        return

    import UMIO

    SWAP_YZ_MATRIX = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
        
    fbx_mesh = UMIO.UMMesh()
    fbx_mesh.set_name(mesh_object.name)
    fbx_mesh.set_id(obj.next_id())
       
    mesh = mesh_object.data
    uv_layer = []
    if mesh.uv_layers.active != None:
        for layer in mesh.uv_layers.active.data:
            uv_layer.append(layer)
                
    basis_mesh = mesh #BPyMesh.getMeshFromObject(mesh_object, None, True, True, self.scene)

    mesh_rot = mesh_object.matrix_basis.to_quaternion().to_matrix().inverted()
    for v in mesh.vertices:
        co = SWAP_YZ_MATRIX.inverted() * v.co * mesh_rot
        no = SWAP_YZ_MATRIX.inverted() * v.normal * mesh_rot
        fbx_mesh.add_vertex(co)
        fbx_mesh.add_normal(no)

    for uv_loop in uv_layer:
        fbx_mesh.add_uv(uv_loop.uv)

    for i, poly in enumerate(mesh.polygons):
        vertex_index = []
        for loop_index in range(poly.loop_start, poly.loop_start+poly.loop_total):
            vi = mesh.loops[loop_index].vertex_index
            vertex_index.append(vi)
        fbx_mesh.add_vertex_index(vertex_index)
        fbx_mesh.add_material_index(poly.material_index)
    
    for material in mesh.materials:
        fbx_material = UMIO.UMMaterial()
                
        fbx_material.set_diffuse(to_umvec(material.diffuse_color))
        fbx_material.set_diffuse_factor(1)
        fbx_material.set_specular(to_umvec(material.specular_color))
        fbx_material.set_emissive(to_umvec(material.mirror_color))
        fbx_material.set_transparency_factor(material.alpha)
        fbx_material.set_shininess(material.specular_intensity)
        
        textures = []
        for texture_slot in material.texture_slots:
            if texture_slot != None:
                if texture_slot.use:
                    textures.append(texture_slot)
        
        if len(textures) > 0:
            texture = textures[0]
            tex = texture.texture
            if tex == None:
                break
            if not hasattr(tex, "image"):
                break
            img = tex.image
            if img == None:
                break
            
            fbx_texture = UMIO.UMTexture()
            fbx_texture.set_file_name(img.filepath)
            fbx_texture.set_name(tex.name)
            fbx_material.add_texture(fbx_texture)
            #print(img.filepath)
            
        fbx_mesh.add_material(fbx_material)

    loc, rot, sca = (SWAP_YZ_MATRIX.inverted() * mesh_object.matrix_basis).decompose()
    fbx_mesh.set_local_translation(to_umvec(loc))
    fbx_mesh.set_local_scaling(to_umvec(sca))
    xyz_rot = rot.normalized().to_euler('XYZ')
    xyz_degree = [math.degrees(xyz_rot.x), math.degrees(xyz_rot.y), math.degrees(xyz_rot.z)]
    fbx_mesh.set_local_rotation(to_umvec(xyz_rot))
    """
    print('vi', len(fbx_mesh.vertex_index_list()))
    print('v', len(fbx_mesh.vertex_list()))
    print('n', len(fbx_mesh.normal_list()))
    print('uv', len(fbx_mesh.uv_list()))
    print('mi', len(fbx_mesh.material_index_list()))
    print('mat', len(fbx_mesh.material_list()))
    """
    export_skin(obj, fbx_mesh, mesh_object, context)
    export_shape_key(obj, fbx_mesh, mesh_object, context)
    #print('skin', len(fbx_mesh.skin_list()))
    
    obj.add_mesh(fbx_mesh)
       
def export_bos_fbx(\
        file, \
        context, \
        is_text, \
        only_selected, \
        imported_node_property, \
        fit_node_length, \
        fbx_version):

    binary_dir = os.path.dirname(bpy.app.binary_path)
    binary_path = binary_dir
    bos_out_path = binary_dir
    is_found_converter = False
    is_fbx = False

    if "64bit" in platform.architecture()[0]:
        um_folder = os.path.dirname(os.path.abspath(__file__))
        um_folder = os.path.join(um_folder, "win64bit")
        if sys.version_info[:2] == (3, 7):
            um_folder = os.path.join(um_folder, "python37")
        if sys.version_info[:2] == (3, 6):
            um_folder = os.path.join(um_folder, "python36")
        if sys.version_info[:2] == (3, 5):
            um_folder = os.path.join(um_folder, "python35")
        if sys.version_info[:2] == (3, 4):
            um_folder = os.path.join(um_folder, "python34")
        if sys.version_info[:2] == (3, 3):
            um_folder = os.path.join(um_folder, "python33")
        if sys.version_info[:2] == (3, 2):
            um_folder = os.path.join(um_folder, "python32")
        if um_folder not in sys.path:
            sys.path.insert(0, um_folder)
        import UMIO

        binary_dir = os.path.join(binary_dir, "umconv")
        #if fbx_version == "FBX SDK 2011":
        #    binary_path = os.path.join(binary_dir, "umconv_bos_fbx2011_win64.exe")
        #if fbx_version == "FBX SDK 2013":
        #    binary_path = os.path.join(binary_dir, "umconv_bos_fbx2013_win64.exe")
        #if fbx_version == "FBX SDK 2015":
        #    binary_path = os.path.join(binary_dir, "umconv_bos_fbx2015_win64.exe")
        if fbx_version == "FBX SDK 2018":
            binary_path = os.path.join(binary_dir, "umconv_bos_fbx2018_win64.exe")
        if fbx_version == "FBX SDK 2017":
            binary_path = os.path.join(binary_dir, "umconv_bos_fbx2017_win64.exe")
        is_found_converter = os.path.exists(binary_path)

    else:
        um_folder = os.path.dirname(os.path.abspath(__file__))
        um_folder = os.path.join(um_folder, "win32bit")
        if sys.version_info[:2] == (3, 4):
            um_folder = os.path.join(um_folder, "python34")
        if sys.version_info[:2] == (3, 3):
            um_folder = os.path.join(um_folder, "python33")
        if sys.version_info[:2] == (3, 2):
            um_folder = os.path.join(um_folder, "python32")
        if um_folder not in sys.path:
            sys.path.insert(0, um_folder)
        import UMIO

        binary_dir = os.path.join(binary_dir, "umconv")
        #if fbx_version == "FBX SDK 2011":
        #    binary_path = os.path.join(binary_dir, "umconv_bos_fbx2011_win32.exe")
        #if fbx_version == "FBX SDK 2013":
        #    binary_path = os.path.join(binary_dir, "umconv_bos_fbx2013_win32.exe")
        if fbx_version == "FBX SDK 2015":
            binary_path = os.path.join(binary_dir, "umconv_bos_fbx2015_win32.exe")
        is_found_converter = os.path.exists(binary_path)

    bos_tempfile = tempfile.TemporaryFile()
    bos_out_path = bos_tempfile.name + ".bos"
    bos_tempfile.close()

    obj = UMIO.UMObject.create_object()
    if obj == None:
        return
    
    armature_objects = []
    if only_selected:
    	armature_objects = [ob for ob in bpy.data.objects if ob.type == 'ARMATURE' and ob.select]
    else:
        armature_objects = [ob for ob in bpy.data.objects if ob.type == 'ARMATURE']
    for armature_object in armature_objects:
        export_armature(obj, armature_object, context, imported_node_property, fit_node_length)

    mesh_objects = []
    if only_selected:
        mesh_objects = [ob for ob in bpy.data.objects if ob.type == 'MESH' and ob.select] 
    else:
        mesh_objects = [ob for ob in bpy.data.objects if ob.type == 'MESH']
    for mesh_object in mesh_objects:
        export_mesh(obj, mesh_object, context)

    umio = UMIO.UMIO()
    setting = UMIO.UMIOSetting()
    setting_tempfile = tempfile.TemporaryFile()
    setting_path = setting_tempfile.name + ".setting"
    setting_tempfile.close()
    setting.set_bl_exp_bool_prop(UMIO.UMIOSetting.UMExpFBX, False)
    setting.set_bl_exp_bool_prop(UMIO.UMIOSetting.UMExpText, is_text)
    
    # save bos
    if not umio.save(bos_out_path, obj, setting):
        print("save bos failed")
        return

    if is_found_converter and os.path.exists(bos_out_path):
        setting.set_bl_imp_bool_prop(UMIO.UMIOSetting.UMImpFBX, False)
        setting.set_bl_exp_bool_prop(UMIO.UMIOSetting.UMExpFBX, True)

        # save setting
        if not umio.save_setting(setting_path, setting):
            print("save", setting_path, "failed")
            return

        # convert bos to fbx
        win_command_flag = 'start /b /normal /WAIT \"\" '
        commad = '\"' +binary_path + '\"'
        commad += ' \"' +bos_out_path+ '\"'
        commad += ' \"' +file+ '\"'
        commad += ' \"' +setting_path+ '\"'
        print(win_command_flag + commad)
        os.system(win_command_flag + commad)
        
        os.remove(bos_out_path)

    if os.path.exists(setting_path):
        os.remove(setting_path)
