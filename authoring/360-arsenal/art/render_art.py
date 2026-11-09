"""Render actual authored scene geometry/UVs using Blender Cycles."""
from pathlib import Path
import bpy,json,math,sys
from mathutils import Vector,Euler

ART=Path(__file__).resolve().parent

def setup():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.resolution_x=640;scene.render.resolution_y=420;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
    scene.view_settings.view_transform='Standard'
    world=bpy.data.worlds.new('Arsenal original studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.6,.69,.8,1);world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
    for name,loc,power,size in [('Key',(-30,-60,100),100000,90),('Fill',(20,80,40),70000,75),('Rim',(-65,30,70),90000,65)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
        ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((-8,0,0))-ob.location).to_track_quat('-Z','Y').to_euler()
    camera=bpy.data.cameras.new('Arsenal inventory camera');cam=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(cam);scene.camera=cam;camera.type='ORTHO'
    return scene,cam

def material(name,texture,bright=False):
    m=bpy.data.materials.new(name);m.use_nodes=True;t=m.node_tree;tex=t.nodes.new('ShaderNodeTexImage');tex.image=texture;tex.interpolation='Closest'
    if bright:
        t.nodes.remove(t.nodes['Principled BSDF']);shader=t.nodes.new('ShaderNodeEmission');shader.inputs['Strength'].default_value=1;t.links.new(tex.outputs['Color'],shader.inputs['Color']);t.links.new(shader.outputs[0],t.nodes['Material Output'].inputs['Surface'])
    else:
        shader=t.nodes['Principled BSDF'];t.links.new(tex.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Roughness'].default_value=.72;shader.inputs['Specular IOR Level'].default_value=.16
    return m

def make_part(p,mat,texture_height):
    signs=[(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
    faces=[('front',(0,1,2,3)),('back',(5,4,7,6)),('left',(4,0,3,7)),('right',(1,5,6,2)),('top',(3,2,6,7)),('bottom',(4,5,1,0))]
    rot=Euler(tuple(math.radians(v) for v in p['rotation']),'XYZ').to_matrix();center=Vector(p['center']);verts=[]
    for s in signs:
        v=rot@Vector(tuple(s[i]*p['size'][i]/2 for i in range(3)))+center;verts.append((v.x,v.z,v.y))
    mesh=bpy.data.meshes.new(p['name']);mesh.from_pydata(verts,[],[f[1] for f in faces]);mesh.materials.append(mat);mesh.uv_layers.new(name='Authored native cube atlas')
    for polygon,(face,_) in zip(mesh.polygons,faces):
        u,v,uu,vv=p['uv'][face];uv=[(u/512,1-vv/texture_height),(uu/512,1-vv/texture_height),(uu/512,1-v/texture_height),(u/512,1-v/texture_height)]
        for loop,point in zip(polygon.loop_indices,uv):mesh.uv_layers.active.data[loop].uv=point
    ob=bpy.data.objects.new(p['name'],mesh);scene=bpy.context.scene;scene.collection.objects.link(ob);return ob,verts

def main():
    scene,cam=setup();catalog=json.loads((ART/'artcatalog.json').read_text());selected=set(sys.argv[sys.argv.index('--')+1:]) if '--' in sys.argv else set()
    for a in catalog['assets']+catalog['ammo']:
        stem=Path(a['scene']).name.removesuffix('.scene.json')
        if selected and a['family'] not in selected and stem not in selected and not ('legendary' in selected and a.get('quality')=='Legendary'):continue
        data=json.loads((ART/a['scene']).read_text());texture=bpy.data.images.load(str(ART/'Common'/a['texture']));lit=material(stem,texture);bright=material(stem+'_fullbright',texture,True);objects=[];verts=[]
        for p in data['parts']:
            ob,v=make_part(p,bright if p.get('shading_mode')=='fullbright' else lit,texture.size[1]);objects.append(ob);verts+=v
        lo=Vector(tuple(min(v[i] for v in verts) for i in range(3)));hi=Vector(tuple(max(v[i] for v in verts) for i in range(3)));center=(lo+hi)/2
        cam.location=center+Vector((30,-130,60));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();inv=cam.rotation_euler.to_matrix().transposed();view=[inv@(Vector(v)-center) for v in verts]
        width=max(v.x for v in view)-min(v.x for v in view);height=max(v.y for v in view)-min(v.y for v in view)
        ratio=scene.render.resolution_x/scene.render.resolution_y;cam.data.ortho_scale=max(width,height*ratio)*1.12
        (ART/'previews').mkdir(exist_ok=True);scene.render.filepath=str(ART/'previews'/f'{stem}.png');bpy.ops.render.render(write_still=True)
        print('ARSENAL_RENDER '+stem,flush=True)
        for ob in objects:bpy.data.objects.remove(ob,do_unlink=True)
        bpy.data.materials.remove(lit);bpy.data.materials.remove(bright);bpy.data.images.remove(texture)
    print('ARSENAL_ART_RENDERED',flush=True)

if __name__=='__main__':main()
