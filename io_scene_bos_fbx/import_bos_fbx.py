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
from bpy_extras.io_utils import unpack_list
import time

def to_list(um_vec):
    return [um_vec.x, um_vec.y, um_vec.z, um_vec.w]

def to_blender_matrix(um_mat):
    mat = mathutils.Matrix()
    for i in range(4):
        for k in range(4):
            mat[k][i] = um_mat.get(i,k)
    return mat

def unpack_face_list_fix(list_of_tuples):
    #allocate the entire list
    flat_ls = [0] * (len(list_of_tuples) * 4)
    i = 0

    for t in list_of_tuples:
        if len(t) == 3:
            t = t[0], t[1], t[2], 0
        else:
            t = t[0], t[1], t[2], t[3]
        flat_ls[i:i + len(t)] = t
        i += 4
    return flat_ls

def import_shape_keys(mesh, blmesh):
    blend_shapes = mesh.blend_shape_list()
    if len(blend_shapes) > 0:
        # add shape key basis
        bpy.ops.object.shape_key_add(from_mix=False)
        shape_basis = None
        if blmesh.shape_keys != None:
            for shape in blmesh.shape_keys.key_blocks:
                shape_basis = shape
        if shape_basis == None:
            return
        
        setted_shapes = [shape_basis]
        
        for blend_shape in blend_shapes:
            blmesh.shape_keys.name = blend_shape.name()
            for channel in blend_shape.blend_shape_channel_list():
                for target_shape in channel.target_shape_list():
                    
                    # add shape key
                    bpy.ops.object.shape_key_add(from_mix=False)
                    target_shape_key = None
                    for shape in blmesh.shape_keys.key_blocks:
                        if shape in setted_shapes:
                            continue
                        else:
                            target_shape_key = shape
                            setted_shapes.append(shape)
                    if target_shape_key == None:
                        break
                    
                    # set data
                    target_shape_key.name = target_shape.name()
                    for i, v in enumerate(target_shape.vertex_list()):
                        if i > len(target_shape_key.data)-1:
                            continue
                        target_shape_key.data[i].co = v[0:3]
                    
                    #print("vertexidx", len(target_shape.vertex_index_list()))
                    #print("vertex", len(target_shape.vertex_list()))
                    #print("normalidx", len(target_shape.normal_index_list()))
                    #print("normal", len(target_shape.normal_list()))
    
def import_mesh(file, obj, armature_obj, context):
    SWAP_YZ_MATRIX = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
    
    for mesh_container in obj.mesh_list():
        mesh = mesh_container.data()
        me = bpy.data.meshes.new(mesh.name())
        me_obj = bpy.data.objects.new(mesh.name(),me)
        me_obj.select = True
        context.scene.objects.link(me_obj)
        context.scene.objects.active = me_obj
        print(mesh.name())
        try:
            me.vertices.add(len(mesh.vertex_list()))
            me.vertices.foreach_set("co", unpack_list(mesh.vertex_list()))
            me.vertices.foreach_set("normal", unpack_list(mesh.normal_list()))
            me.tessfaces.add(len(mesh.vertex_index_list()))
            me.tessfaces.foreach_set("vertices_raw", unpack_face_list_fix(mesh.vertex_index_list()))
        except:
            pass

        # material
        for i, material in enumerate(mesh.material_list()):
            mat = bpy.data.materials.new(material.name())
            bpy.ops.object.material_slot_add()
            me_obj.material_slots[i].material = mat
            
            if len(mat.diffuse_color) == len(to_list(material.diffuse())):
                mat.diffuse_color = to_list(material.diffuse())
            if len(mat.specular_color) == len(to_list(material.specular())):
                mat.specular_color = to_list(material.specular())
            if len(mat.mirror_color) == len(to_list(material.emissive())):
                mat.mirror_color = to_list(material.emissive())
            mat.alpha = material.transparency_factor()
            mat.specular_intensity = material.shininess()
            
            # texture
            for k, texture in enumerate(material.texture_list()):    
                try:
                    tex = mat.texture_slots.create(k)
                    tex.texture = bpy.data.textures.new(texture.name(), type='IMAGE')
                    tex.texture_coords = 'UV'
                    tex.use = True
                    tex.use_map_color_diffuse = True
                    fbx_base_path, fbx_file_name = os.path.split(file)
                    fbx_texture_file_path = texture.file_name()
                    fbx_garbage_path, fbx_texture_name = os.path.split(fbx_texture_file_path)
                    base_norm = os.path.normpath(fbx_base_path)
                    garbage_norm = os.path.normpath(fbx_garbage_path)
                    if base_norm in garbage_norm and os.path.exists(fbx_texture_file_path):
                        texture_file_path = fbx_texture_file_path
                    else:
                        texture_file_path = bpy.path.abspath(os.path.join(fbx_base_path, fbx_texture_name))
                    texture_file_path = os.path.normpath(texture_file_path)
                    if os.path.exists(texture_file_path):
                        tex.texture.image = bpy.data.images.load(texture_file_path)
                except:
                    pass

        # material index
        for i, index in enumerate(mesh.material_index_list()):
            me.tessfaces[i].material_index = index
            
        # uv
        layered_uv_list = mesh.layered_uv_list()
        for i, uv_layer in enumerate(layered_uv_list):
            me.tessface_uv_textures.new()
            uvs = uv_layer
            if len(uvs) == 0:
                continue
            ttex = me.tessface_uv_textures[i]
            count = 0
            for k, face in enumerate(mesh.vertex_index_list()):
                tface = ttex.data[k]
                tessFace = me.tessfaces[k]
                mat = me_obj.material_slots[tessFace.material_index].material
                if mat.texture_slots[i] != None:
                    tface.image = mat.texture_slots[i].texture.image
                vcount = len(face)
                if vcount == 3:
                    tface.uv1 = uvs[count]
                    count = count + 1
                    tface.uv2 = uvs[count]
                    count = count + 1
                    tface.uv3 = uvs[count]
                    count = count + 1
                elif vcount == 4:
                    tface.uv1 = uvs[count]
                    count = count + 1
                    tface.uv2 = uvs[count]
                    count = count + 1
                    tface.uv3 = uvs[count]
                    count = count + 1
                    tface.uv4 = uvs[count]
                    count = count + 1
                else:
                    count = count + vcount
        
        #print("skey start")
        # shape keys
        import_shape_keys(mesh, me)
        #print("skey end")
            
        me.update(calc_edges=True)
        global_trans = to_blender_matrix(mesh.global_transform())
        me_obj.matrix_basis = SWAP_YZ_MATRIX * global_trans
        
        # calculate normalized weight
        normalized_weights = {}
        #print("skins:", len(mesh.skin_list()))
        for i, skin in enumerate(mesh.skin_list()):
            #print("clusters:", len(skin.cluster_list()))
            for k, cluster in enumerate(skin.cluster_list()):
                for n, index in enumerate(cluster.index_list()):
                    weight = cluster.weight_list()[n]
                    #print("weight:", weight)
                    if not (index in normalized_weights):
                        normalized_weights[index] = 0.0
                    normalized_weights[index] = normalized_weights[index] + weight
                    
        # create bone group
        for i, skin in enumerate(mesh.skin_list()):

            #print("mesh:", mesh.id())
            #print("geometry_node_id:",  skin.geometry_node_id())
            if mesh.id() != skin.geometry_node_id():
                continue
            #print(skin.cluster_list())
            for k, cluster in enumerate(skin.cluster_list()):
                link_node = cluster.link_node()
                #print("link_node:", link_node)
                #print("link_node_id:",  cluster.link_node_id())
                if link_node == None:
                    continue
                link_name = cluster.link_node().name().split(' ')[-1]
                #print("link:", link_name)

                # use existing group or new
                group = None
                if link_name in me_obj.vertex_groups.keys():
                    group = me_obj.vertex_groups[link_name]
                if group == None:
                    group = me_obj.vertex_groups.new(link_name)
                    
                for n, index in enumerate(cluster.index_list()):
                    weight = cluster.weight_list()[n]
                    
                    if normalized_weights[index] > 0:
                        group.add([index], weight/normalized_weights[index], 'ADD')
                    else:
                        group.add([index], weight, 'ADD')
        # modifier
        if armature_obj != None:
            modifier = me_obj.modifiers.new('Armature', 'ARMATURE')
            modifier.object = armature_obj
    
def import_armature(file, obj, context):
    SWAP_YZ_MATRIX = mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X')
    
    if len(obj.skeleton_list()) == 0:
        return
    
    armature = bpy.data.armatures.new("armature")
    armature_obj = bpy.data.objects.new("armature", armature)
    armature_obj.select = True
    context.scene.objects.link(armature_obj)
    context.scene.objects.active = armature_obj
    armature.draw_type = 'STICK'
    armature.show_axes = True
    armature_obj.show_x_ray = True
    
    if not bpy.ops.object.mode_set.poll():
        return
    
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    # create {id, bone} dic
    bone_dic = {}
    for skeleton_contanier in obj.skeleton_list():
        skeleton = skeleton_contanier.data()
        id = skeleton.id()
        parent = skeleton.parent()
        bone = armature.edit_bones.new(skeleton.name())
        bone_dic[id] = bone
        
        mat = to_blender_matrix(skeleton.global_transform())
        bone.transform(SWAP_YZ_MATRIX * mat)
            
    # set parent
    for skeleton_contanier in obj.skeleton_list():
        skeleton = skeleton_contanier.data()
        bone = bone_dic[skeleton.id()]
        if skeleton.parent_id() in bone_dic.keys():
            bone.parent = bone_dic[skeleton.parent_id()]

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
        
    # detect bone position and length
    for skeleton_contanier in obj.skeleton_list():
        skeleton = skeleton_contanier.data()
        bone = bone_dic[skeleton.id()]
        if len(bone.children) == 1:
            bone.tail = bone.children[0].head
        else:
            bone.tail = bone.head + mathutils.Vector([0,0,-0.1])

        bone.use_inherit_scale = False
        bone.fbx_local_translation_x = skeleton.local_translation().x
        bone.fbx_local_translation_y = skeleton.local_translation().y
        bone.fbx_local_translation_z = skeleton.local_translation().z
        bone.fbx_local_rotation_x = skeleton.local_rotation().x
        bone.fbx_local_rotation_y = skeleton.local_rotation().y
        bone.fbx_local_rotation_z = skeleton.local_rotation().z
        bone.fbx_local_scaling_x = skeleton.local_scaling().x
        bone.fbx_local_scaling_y = skeleton.local_scaling().y
        bone.fbx_local_scaling_z = skeleton.local_scaling().z
        '''
        bone.fbx_rotation_offset = skeleton.rotation_offset()[0:3]
        bone.fbx_rotation_pivot = skeleton.rotation_pivot()[0:3]
        bone.fbx_pre_rotation = skeleton.pre_rotation()[0:3]
        bone.fbx_post_rotation = skeleton.post_rotation()[0:3]
        bone.fbx_scaling_offset = skeleton.scaling_offset()[0:3]
        bone.fbx_scaling_pivot = skeleton.scaling_pivot()[0:3]
        bone.fbx_geometric_translation = skeleton.geometric_translation()[0:3]
        bone.fbx_geometric_rotation = skeleton.geometric_rotation()[0:3]
        bone.fbx_geometric_scaling = skeleton.geometric_scaling()[0:3]
        '''
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        
    return armature_obj

def imoprt_camera(file, obj, context):
    for camera_container in obj.camera_list():
        camera = camera_container.data()
        

def import_bos_fbx(file, context, triangulate):
    time1 = time.time()

    binary_dir = os.path.dirname(bpy.app.binary_path)
    binary_path = binary_dir
    bos_out_path = binary_dir
    is_found_converter = False
    is_fbx = False

    root, ext = os.path.splitext(file)
    is_fbx = ("fbx" in ext or "FBX" in ext)


    print("start")
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
        if sys.version_info[:2] == (3, 7):
          binary_path = os.path.join(binary_dir, "umconv_bos_fbx2018_win64.exe")
        if sys.version_info[:2] == (3, 6):
          binary_path = os.path.join(binary_dir, "umconv_bos_fbx2018_win64.exe")
        if sys.version_info[:2] == (3, 5):
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
        binary_path = os.path.join(binary_dir, "umconv_bos_fbx2015_win32.exe")
        is_found_converter = os.path.exists(binary_path)

    bos_tempfile = tempfile.TemporaryFile()
    bos_out_path = bos_tempfile.name + ".bos"
    bos_tempfile.close()

    # save import setting
    umio = UMIO.UMIO()
    setting = UMIO.UMIOSetting()
    setting_tempfile = tempfile.TemporaryFile()
    setting_path = setting_tempfile.name + ".setting"
    setting_tempfile.close()
    setting.set_bl_imp_bool_prop(UMIO.UMIOSetting.UMImpTriangulate, triangulate)
    setting.set_bl_imp_bool_prop(UMIO.UMIOSetting.UMImpNurbs, True)
    setting.set_bl_imp_bool_prop(UMIO.UMIOSetting.UMImpPatch, True)

    if is_found_converter and is_fbx:
        setting.set_bl_imp_bool_prop(UMIO.UMIOSetting.UMImpFBX, True)
        setting.set_bl_exp_bool_prop(UMIO.UMIOSetting.UMExpFBX, False)

        # save settings
        print("save import setting...")
        if not umio.save_setting(setting_path, setting):
            print("save", setting_path, "failed")
            return

        # convert fbx to bos
        print("convert fbx to bos...")
        win_command_flag = 'start /b /normal /WAIT \"\" '
        commad = '\"' +binary_path + '\"'
        commad += ' \"' +file+ '\"'
        commad += ' \"' +bos_out_path+ '\"'
        commad += ' \"' +setting_path+ '\"'
        print(win_command_flag + commad)
        os.system(win_command_flag + commad)

    setting.set_bl_imp_bool_prop(UMIO.UMIOSetting.UMImpFBX, False)
    obj = umio.load(bos_out_path, setting)
    if obj == None:
        return

    if is_found_converter and is_fbx:
        os.remove(bos_out_path)


#    print("import_camera")
#    imoprt_camera(file, obj, context)
    
    armature_obj = import_armature(file, obj, context)
    import_mesh(file, obj, armature_obj, context)

    bpy.ops.object.shade_smooth()

    if os.path.exists(setting_path):
        os.remove(setting_path)

    print("time is ", time.time() - time1)
