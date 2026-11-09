"""Render the exact authored native cuboids/UVs in Blender for review."""
from pathlib import Path
import json,math
import bpy
from mathutils import Euler,Vector

ROOT=Path(__file__).resolve().parents[1]

def setup():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
    scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast'
    world=bpy.data.worlds.new('Armor display review studio');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.61,.68,.76,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.6;scene.world=world
    for name,loc,power,size in [('Key',(-70,-90,110),100000,80),('Fill',(70,-30,60),45000,90),('Rim',(0,90,95),80000,70)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
        ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=loc
        ob.rotation_euler=(Vector((0,0,30))-ob.location).to_track_quat('-Z','Y').to_euler()
    cam=bpy.data.objects.new('Review camera',bpy.data.cameras.new('Review camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO'
    return scene

def material(image):
    mat=bpy.data.materials.new('Authored original pixel atlas');mat.use_nodes=True
    tree=mat.node_tree;shader=tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value=.85;shader.inputs['Specular IOR Level'].default_value=.12
    tex=tree.nodes.new('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest'
    tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
    return mat

def mesh_part(p,mat,atlas_size):
    corners=[(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
    faces=[('front',(0,1,2,3)),('back',(5,4,7,6)),('left',(4,0,3,7)),('right',(1,5,6,2)),('top',(3,2,6,7)),('bottom',(4,5,1,0))]
    rotation=Euler(tuple(math.radians(v) for v in p['rotation']),'XYZ').to_matrix();center=Vector(p['center']);verts=[]
    for c in corners:
        v=rotation@Vector(tuple(c[a]*p['size'][a]/2 for a in range(3)))+center
        verts.append((v.x,v.z,v.y))
    mesh=bpy.data.meshes.new(p['name']);mesh.from_pydata(verts,[],[list(f[1]) for f in faces]);mesh.materials.append(mat);mesh.uv_layers.new(name='Exact native atlas')
    for polygon,(face,_) in zip(mesh.polygons,faces):
        u,v,u2,v2=p['uv'][face];uv=[(u/atlas_size,1-v2/atlas_size),(u2/atlas_size,1-v2/atlas_size),(u2/atlas_size,1-v/atlas_size),(u/atlas_size,1-v/atlas_size)]
        for loop,point in zip(polygon.loop_indices,uv):mesh.uv_layers.active.data[loop].uv=point
    ob=bpy.data.objects.new(p['name'],mesh);bpy.context.collection.objects.link(ob)

def main():
    contract=json.loads((ROOT/'art-contract.json').read_text())
    out=ROOT/'previews';out.mkdir(exist_ok=True)
    for a in contract['assets']:
        data=json.loads((ROOT/'source'/(a['id']+'.scene.json')).read_text());scene=setup()
        image=bpy.data.images.load(data['texture']);mat=material(image)
        for p in data['parts']:mesh_part(p,mat,data['atlas_size'])
        if a['kind']=='holder':target=(0,10,12);scale=43;angles=[(-100,-150,90),(0,-150,48),(110,150,75)]
        elif a['kind']=='rack':target=(0,10,30);scale=85;angles=[(-110,-160,100),(0,-160,66),(110,150,90)]
        else:target=(0,0,31);scale=79;angles=[(-100,-150,87),(0,-160,66),(100,150,87)]
        for title,location in zip(('Front_Left','Front','Rear_Right'),angles):
            scene.camera.location=location;scene.camera.rotation_euler=(Vector(target)-scene.camera.location).to_track_quat('-Z','Y').to_euler()
            scene.camera.data.ortho_scale=scale;scene.render.filepath=str(out/(a['id']+'_'+title+'.png'));bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source'/(a['id']+'.blend')))
        print('DISPLAY_RENDERED '+a['id'],flush=True)

if __name__=='__main__':main()
