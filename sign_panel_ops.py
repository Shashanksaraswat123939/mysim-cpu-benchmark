import math,json,statistics
from pathlib import Path
from mathutils import Vector
from sign_profile_geometry import construct
SUPPORTED='26d2a66fd51dc1e10a731ebb'
def sign_geometry(obj,recipe):
 assert recipe['procedure_id']==SUPPORTED,'Sign profile operator only validated against explicitly annotated source'
 mesh=obj.data;assert len(mesh.vertices)==38 and len(mesh.polygons)==28,'Annotated billboard inventory changed';assert len(mesh.uv_layers)==2;frontfaces=set(range(10,18));frontvertices=sorted({i for p in mesh.polygons if p.index in frontfaces for i in p.vertices});assert len(frontvertices)==10;positions=[v.co.copy() for v in mesh.vertices];span=max(max(v[a] for v in positions)-min(v[a] for v in positions) for a in range(3));tol=span*1e-8;normals={i:Vector() for i in frontvertices}
 for face in mesh.polygons:
  if face.index in frontfaces:
   for i in face.vertices:normals[i]+=face.normal*face.area
 normals={i:n.normalized() for i,n in normals.items()};pairs={};frontmap={};weights={};vertex_uv={}
 for face in mesh.polygons:
  for i,loop in zip(face.vertices,face.loop_indices):vertex_uv.setdefault(i,[tuple(layer.data[loop].uv) for layer in mesh.uv_layers])
 for i,p in enumerate(positions):
  nearest=min(frontvertices,key=lambda k:(positions[k]-p).length);distance=(positions[nearest]-p).length;frontmap[i]=nearest;weights[i]=1.0 if distance<=tol else 0.0
  if distance>tol:
   assert distance<span*.01,'Source includes unannotated support or separate component';previous=pairs.get(nearest)
   if previous is not None:assert (positions[previous]-p).length<=tol,'Ambiguous measured back rim'
   pairs[nearest]=i
 assert set(pairs)==set(frontvertices),'Measured rear rim incomplete';thicknesses=[abs((positions[k]-positions[v]).dot(normals[k])) for k,v in pairs.items()];thickness=statistics.median(thicknesses);assert min(thicknesses)>0 and max(thicknesses)/min(thicknesses)<1.1,'Nonuniform profile requires separate annotation';depth=thickness*.2;surfaces=[]
 for face in mesh.polygons:
  corners=[]
  for i,loop in zip(face.vertices,face.loop_indices):corners.append(dict(position=tuple(positions[i]),u=float(mesh.uv_layers[0].data[loop].uv.x),uv=[tuple(layer.data[loop].uv) for layer in mesh.uv_layers],normal=tuple(normals[frontmap[i]]),front=weights[i]))
  surfaces.append(dict(corners=corners,source_polygon=face.index))
 # Close the actual measured rear rim; no guessed rear thickness or support posts.
 for face in mesh.polygons:
  if face.index not in frontfaces:continue
  corners=[]
  for i in reversed(face.vertices):
   back=pairs[i];uv=vertex_uv[back];corners.append(dict(position=tuple(positions[back]),u=float(vertex_uv[i][0][0]),uv=uv,normal=tuple(normals[i]),front=0.0))
  surfaces.append(dict(corners=corners,source_polygon=-1))
 result=construct(surfaces,[k/8 for k in range(1,8)],1/512,depth,tol);folder=Path(recipe['_diagnostic_directory']);(folder/'sign-profile-topology.json').write_text(json.dumps({k:v for k,v in result.items() if k not in ['vertices','faces','corner_uv']},indent=2));assert not result['nonmanifold_edges'],'Sign source-profile shell has nonmanifold edges';assert result['changed_corner_occurrences']>0
 old=mesh;new=old.copy();new.clear_geometry();new.from_pydata(result['vertices'],[],result['faces']);new.update()
 for layer in list(new.uv_layers):new.uv_layers.remove(layer)
 for index,original_layer in enumerate(old.uv_layers):
  layer=new.uv_layers.new(name=original_layer.name)
  for face,corners in zip(new.polygons,result['corner_uv']):
   for loop,uv in zip(face.loop_indices,corners):layer.data[loop].uv=uv[index]
 existing=new.attributes.get('source_polygon_id')
 if existing:new.attributes.remove(existing)
 attribute=new.attributes.new(name='source_polygon_id',type='INT',domain='FACE')
 for i,source_polygon in enumerate(result['source_polygons']):attribute.data[i].value=source_polygon
 obj.data=new;obj['validate_source_face_provenance']=True;obj['sign_measured_relative_depth']=depth;obj['sign_measured_backing_thickness']=thickness;obj['sign_joint_count']=7;obj['drain_source_normal_world']=list((obj.matrix_world.to_3x3().inverted().transposed()@sum(normals.values(),Vector()).normalized()).normalized());obj['sign_operator_scope']='one annotated original billboard body only; no invented fixtures';return ['source_billboard_front_and_four_profile_edges_reconstructed','seven_texture_evidenced_rounded_physical_panel_joints','rear_closed_at_original_measured_rim','original_curve_material_ST_and_all_UVs_preserved','no_invented_supports_fasteners_or_branding_changes']
