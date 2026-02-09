import subprocess
import os
import json

class UniversalFBXAnaliser:
    @staticmethod
    def check_file(filepath, settings, fix_mode=False, blender_path=""):
        if not blender_path or not os.path.exists(blender_path):
            return [{"name": "Erreur", "status": "Fail", "errors": ["Blender.exe introuvable"]}]

        settings_str = json.dumps(settings)
        fix_val = "True" if fix_mode else "False"

        script_content = f"""
import bpy
import json
import bmesh
from mathutils import Vector

def calculate_uv_area(uvs):
    area = 0.0
    for i in range(len(uvs)):
        j = (i + 1) % len(uvs)
        area += uvs[i].x * uvs[j].y
        area -= uvs[j].x * uvs[i].y
    return abs(area) / 2.0

def run_qa():
    settings = json.loads('{settings_str}')
    fix_active = {fix_val}
    path = r"{filepath}"
    
    scan_p_mode = settings.get('scan_pivot_mode', 'Bottom Center')
    fix_p_mode = settings.get('fix_pivot_mode', 'Bottom Center')
    
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    try:
        bpy.ops.import_scene.fbx(filepath=path)
        results = []
        all_objs = bpy.data.objects
        props = [o for o in all_objs if o.type == 'MESH' and not o.name.startswith('UCX_')]
        prop_names = [p.name for p in props]
        modified = False

        for obj in props:
            errs = []
            bpy.context.view_layer.objects.active = obj
            
            # naming
            target_prefix = settings.get('name_prefix', 'SM_')
            if settings.get('check_name'):
                if not obj.name.startswith(target_prefix):
                    if fix_active and settings.get('fix_name'):
                        obj.name = f"{{target_prefix}}{{obj.name}}"
                        modified = True
                    else:
                        errs.append(f"Nom invalide (Attendu: {{target_prefix}}...)")

            # pivot
            world_verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
            if not world_verts:
                z_min, z_max = 0, 0
            else:
                z_min, z_max = min([v.z for v in world_verts]), max([v.z for v in world_verts])
            
            if settings.get('check_pivot'):
                scan_target_z = z_min
                if scan_p_mode == "Center": scan_target_z = (z_min + z_max) / 2
                elif scan_p_mode == "Top Center": scan_target_z = z_max

                if abs(obj.location.z - scan_target_z) > 0.001 or abs(obj.location.x) > 0.001:
                    if fix_active and settings.get('fix_pivot'):
                        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
                        bpy.ops.object.mode_set(mode='EDIT')
                        bpy.ops.mesh.select_all(action='SELECT')
                        
                        height = z_max - z_min
                        offset_z = 0
                        if fix_p_mode == "Bottom Center": offset_z = height / 2
                        elif fix_p_mode == "Top Center": offset_z = -height / 2
                        
                        bpy.ops.transform.translate(value=(0, 0, offset_z))
                        bpy.ops.object.mode_set(mode='OBJECT')
                        obj.location = (0,0,0)
                        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                        modified = True
                    else:
                        errs.append(f"Pivot incorrect (attendu: {{scan_p_mode}})")

            # ngons
            has_ngons = any(len(p.vertices) > 4 for p in obj.data.polygons)
            if settings.get('check_ngon') and has_ngons:
                if fix_active and settings.get('fix_ngon'):
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.quads_convert_to_tris()
                    bpy.ops.object.mode_set(mode='OBJECT')
                    modified = True
                else:
                    errs.append("NGons détectés")

            # UV check
            if settings.get('check_uvs'):
                has_uv_error = False
                uv_msg = ""
                
                # check uv map exist
                if len(obj.data.uv_layers) == 0:
                    has_uv_error = True
                    uv_msg = "Pas d'UV map"
                else:
                    # analyse
                    bm = bmesh.new()
                    bm.from_mesh(obj.data)
                    uv_layer = bm.loops.layers.uv.verify()
                    
                    uv_centers = []
                    
                    for face in bm.faces:
                        uvs = [l[uv_layer].uv for l in face.loops]
                        
                        # checkarea 0 
                        area = calculate_uv_area(uvs)
                        if area < 0.000001:
                            has_uv_error = True
                            uv_msg = "UV Area Nulle (Face écrasée)"
                            break
                        
                        # check stacked
                        center = Vector((0,0))
                        for uv in uvs: center += uv
                        center /= len(uvs)
                        center_tuple = (round(center.x, 4), round(center.y, 4))
                        uv_centers.append(center_tuple)
                    
                    bm.free()
                    
                    if not has_uv_error and len(uv_centers) > 1:
                        unique_centers = set(uv_centers)
                        # Tolerance 
                        if len(unique_centers) < len(uv_centers) * 0.9: 
                            has_uv_error = True
                            uv_msg = "UVs Empilés (Stacked/Reset détecté)"
                # fix
                if has_uv_error:
                    if fix_active and settings.get('fix_uvs'):
                        import math
                        user_angle = settings.get('fix_uv_angle', 66.0)
                        angle_rad = math.radians(user_angle)
                        
                        user_margin = settings.get('fix_uv_margin', 0.02)

                        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                        
                        if not obj.data.uv_layers:
                            obj.data.uv_layers.new(name="UVMap")

                        bpy.ops.object.mode_set(mode='EDIT')
                        
                        bpy.ops.mesh.select_all(action='SELECT')
                        bpy.ops.mesh.mark_seam(clear=True)
                        bpy.ops.uv.select_all(action='SELECT')
                        bpy.ops.uv.reset() 
                        
                        bpy.ops.mesh.select_all(action='DESELECT')
                        bpy.ops.mesh.select_mode(type='EDGE')
                        
                        bpy.ops.mesh.edges_select_sharp(sharpness=angle_rad) 
                        bpy.ops.mesh.mark_seam(clear=False) 
                        
                        bpy.ops.mesh.select_all(action='SELECT')
                        bpy.ops.uv.unwrap(method='CONFORMAL', margin=user_margin)
                        
                        bpy.ops.uv.minimize_stretch(iterations=100) 
                        bpy.ops.uv.average_islands_scale()
                        
                        bpy.ops.uv.pack_islands(margin=user_margin, rotate=True)
                        
                        bpy.ops.object.mode_set(mode='OBJECT')
                        modified = True
                    else:
                        errs.append(uv_msg)

            # merge double vertice
            if fix_active and settings.get('fix_double'):
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                pre_count = len(obj.data.vertices)
                bpy.ops.mesh.remove_doubles(threshold=0.0001)
                bpy.ops.object.mode_set(mode='OBJECT')
                if len(obj.data.vertices) < pre_count:
                    modified = True

            # poly count
            if settings.get('check_poly'):
                if len(obj.data.polygons) > settings.get('poly_limit', 10000):
                    errs.append(f"Polycount: {{len(obj.data.polygons)}}")

            # result
            status = "Pass" if len(errs) == 0 else "Fail"
            results.append({{"name": obj.name, "status": status, "errors": errs}})

        # UCX Check
        if settings.get('check_ucx'):
            for o in [obj for obj in all_objs if obj.name.startswith('UCX_')]:
                base_name = o.name[4:]
                if '.' in base_name: base_name = base_name.split('.')[0]
                found = False
                for p_name in prop_names:
                    if p_name in o.name: found = True
                if not found:
                    results.append({{"name": o.name, "status": "Fail", "errors": ["Collision orpheline"]}})

        if fix_active and modified:
            bpy.ops.export_scene.fbx(filepath=path, bake_space_transform=True, axis_forward='-Z', axis_up='Y')

        print("RESULT_START" + json.dumps(results) + "RESULT_END")
    except Exception as e:
        import traceback
        err_msg = str(e)
        print("RESULT_START" + json.dumps([{{'name': 'Error', 'status': 'Fail', 'errors': [err_msg]}}]) + "RESULT_END")

run_qa()
"""
        try:
            process = subprocess.Popen(
                [blender_path, "--background", "--factory-startup", "--python-expr", script_content],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8'
            )
            stdout, stderr = process.communicate()
            
            if "RESULT_START" in stdout:
                try:
                    json_str = stdout.split("RESULT_START")[1].split("RESULT_END")[0]
                    return json.loads(json_str)
                except:
                    return [{"name": "Parse Error", "status": "Fail", "errors": ["Erreur lecture JSON"]}]
            else:
                return [{"name": "Blender Error", "status": "Fail", "errors": [f"Console: {stderr[-300:] if stderr else 'No error info'}"]}]
        except Exception as e:
            return [{"name": "System Error", "status": "Fail", "errors": [str(e)]}]