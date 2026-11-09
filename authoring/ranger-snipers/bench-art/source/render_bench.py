"""Offline Blender render from exact original cube/UV source; no asset edits."""
from pathlib import Path
import json,math
import bpy
from mathutils import Vector,Euler

ROOT=Path(__file__).resolve().parents[1]
def setup():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast'
    world=bpy.data.worlds.new('Gunsmith studio');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.63,.70,.78,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.65;scene.world=world
    for name,loc,power,size in [('Key',(-60,-85,130),105000,100),('Fill',(65,-30,65),60000,90),('Rim',(-20,95,100),95000,80)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
        ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=loc
        ob.rotation_euler=(Vector((0,0,28))-ob.location).to_track_quat('-Z','Y').to_euler()
    camera=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',camera)
    scene.collection.objects.link(cam);scene.camera=cam;camera.type='ORTHO';camera.ortho_scale=92
    return scene

def material(image,fullbright=False):
    mat=bpy.data.materials.new('selected_emissive' if fullbright else 'original_pixel_atlas');mat.use_nodes=True
    tree=mat.node_tree;tree.nodes.clear()
    output=tree.nodes.new('ShaderNodeOutputMaterial');tex=tree.nodes.new('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest'
    if fullbright:
        shader=tree.nodes.new('ShaderNodeEmission');shader.inputs['Strength'].default_value=1.0
        tree.links.new(tex.outputs['Color'],shader.inputs['Color']);tree.links.new(shader.outputs[0],output.inputs['Surface'])
    else:
        shader=tree.nodes.new('ShaderNodeBsdfPrincipled');shader.inputs['Roughness'].default_value=.83
        shader.inputs['Specular IOR Level'].default_value=.13
        tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);tree.links.new(shader.outputs[0],output.inputs['Surface'])
    return mat

def mesh_part(p,mat,atlas_size):
    corners=[(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
    faces=[('front',(0,1,2,3)),('back',(5,4,7,6)),('left',(4,0,3,7)),('right',(1,5,6,2)),('top',(3,2,6,7)),('bottom',(4,5,1,0))]
    rotation=Euler(tuple(math.radians(v) for v in p['rotation']),'XYZ').to_matrix();center=Vector(p['center']);verts=[]
    for c in corners:
        v=rotation@Vector(tuple(c[a]*p['size'][a]/2 for a in range(3)))+center
        verts.append((v.x,v.z,v.y))
    mesh=bpy.data.meshes.new(p['name']);mesh.from_pydata(verts,[],[list(f[1]) for f in faces]);mesh.materials.append(mat)
    mesh.uv_layers.new(name='Exact native atlas')
    for polygon,(face,_) in zip(mesh.polygons,faces):
        u,v,u2,v2=p['uv'][face];uv=[(u/atlas_size,1-v2/atlas_size),(u2/atlas_size,1-v2/atlas_size),(u2/atlas_size,1-v/atlas_size),(u/atlas_size,1-v/atlas_size)]
        for loop,point in zip(polygon.loop_indices,uv):mesh.uv_layers.active.data[loop].uv=point
    ob=bpy.data.objects.new(p['name'],mesh);bpy.context.collection.objects.link(ob)

def main():
    data=json.loads((ROOT/'source/RS_Gunsmith_Bench.scene.json').read_text());scene=setup()
    image=bpy.data.images.load(data['texture']);lit=material(image);glow=material(image,True)
    for p in data['parts']:mesh_part(p,glow if p['shading_mode']=='fullbright' else lit,data['atlas_size'])
    out=ROOT/'previews';out.mkdir(exist_ok=True)
    angles=[('Front_Left',(-105,-145,100),(0,0,29),94),('Front_Right',(115,-135,97),(0,0,29),94),
            ('Rear_Right',(110,150,105),(0,0,29),94),('Worktop_Detail',(85,-130,110),(0,0,43),70)]
    for name,location,target,scale in angles:
        scene.camera.location=location;scene.camera.rotation_euler=(Vector(target)-scene.camera.location).to_track_quat('-Z','Y').to_euler()
        scene.camera.data.ortho_scale=scale;scene.render.filepath=str(out/('RS_Gunsmith_Bench_'+name+'.png'))
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/RS_Gunsmith_Bench.blend'))
    print('GUNSMITH_BENCH_THREE_ANGLES_RENDERED')

if __name__=='__main__':main()
