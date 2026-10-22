"""Strict source-parameter audit for intentionally displaced source surfaces."""
import math

def expected_uv(corners,weights):
 assert len(weights)==3 and len(corners)==3 and all(math.isfinite(x) for x in weights),'Invalid source parameter weights'
 assert abs(sum(weights)-1)<1e-4 and min(weights)>=-1e-4 and max(weights)<=1.0001,'Source parameter outside original triangle'
 return tuple(sum(float(corners[j][axis])*float(weights[j]) for j in range(3)) for axis in range(2))

def audit_source_parameters(candidate,source,world_point):
 mesh=candidate.data;old=source.data;old.calc_loop_triangles();triangles=list(old.loop_triangles);ids=mesh.attributes.get('source_parameter_triangle');parameters=mesh.attributes.get('source_parameter_barycentric')
 assert ids and ids.domain=='FACE' and parameters and parameters.domain=='CORNER','Required full source parameter provenance missing'
 assert len(ids.data)==len(mesh.polygons) and len(parameters.data)==len(mesh.loops),'Incomplete source parameter coverage'
 errors=[[] for _ in old.uv_layers];distances=[];pages=[]
 for face in mesh.polygons:
  index=ids.data[face.index].value;assert 0<=index<len(triangles),'Invalid original source triangle identity';triangle=triangles[index]
  for loop in face.loop_indices:
   weights=list(parameters.data[loop].vector);position=sum((world_point(source,old.vertices[triangle.vertices[j]].co)*weights[j] for j in range(3)),world_point(source,old.vertices[triangle.vertices[0]].co)*0)
   distances.append((world_point(candidate,mesh.vertices[mesh.loops[loop].vertex_index].co)-position).length)
   for layer_index,layer in enumerate(old.uv_layers):
    target=mesh.uv_layers.get(layer.name);assert target,'Source UV layer missing';expected=expected_uv([layer.data[i].uv for i in triangle.loops],weights);actual=target.data[loop].uv;assert all(math.isfinite(x) for x in actual),'Nonfinite output UV';errors[layer_index].append(math.hypot(float(actual.x)-expected[0],float(actual.y)-expected[1]))
    if layer_index==1 and 1e-4<expected[1]%1<1-1e-4:pages.append(math.floor(actual.y)==math.floor(expected[1]))
 assert distances and errors[0],'No provenance-checked output corners'
 scale=max(max(source.dimensions),1e-8);assert max(distances)<=scale*.003,'A generated parameter corner departed from source envelope beyond existing tolerance'
 return dict(scope='all_candidate_corners_against_original_triangle_barycentric_parameters',corner_count=len(distances),all_corners_checked=True,source_parameter_max_distance=max(distances),uv0_samples=len(errors[0]),uv0_max_error=max(errors[0]),uv1_samples=len(errors[1]) if len(errors)>1 else 0,uv1_max_error=max(errors[1]) if len(errors)>1 else 0,uv1_unambiguous_page_samples=len(pages),uv1_unambiguous_page_mismatches=sum(not x for x in pages))
