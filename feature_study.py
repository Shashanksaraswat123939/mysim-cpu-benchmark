"""Evidence for a named feature-design decision, not a reconstruction candidate."""
import bpy,bmesh,sys,os,json,time,hashlib,zipfile,resource,math,statistics
from pathlib import Path
from mathutils import Vector
from release_transport import public_download,release_upload
from detail_ops import make_material
from rebuild_ops import render_review
import import_patch
r=Path.cwd();ident=sys.argv[sys.argv.index('--')+1];job=json.loads((r/'wave-input'/(ident+'.json')).read_text());recipe=job['recipes'][0];sources={x['key']:x for x in json.loads((r/'sources.json').read_text())};source=sources[recipe['source_key']];out=r/'results'/ident;out.mkdir(parents=True,exist_ok=True);start=time.monotonic();wave=os.environ['WAVE'];tag='candidates-wave-'+wave
def fingerprint(obj):
 return hashlib.sha256(json.dumps(dict(vertices=[list(v.co) for v in obj.data.vertices],polygons=[list(p.vertices) for p in obj.data.polygons],uv=[[[*d.uv] for d in layer.data] for layer in obj.data.uv_layers],matrix=[list(row) for row in obj.matrix_world]),separators=(',',':')).encode()).hexdigest()
report=dict(job_id=ident,state='RUNNING',scope='source_feature_design_study',processed=0,failed=0,records=[],failures=[],quality_accepted=False,source_geometry_changed=False,upgrade_count=0)
try:
 cache=r/'feature-cache';cache.mkdir(exist_ok=True);archive=cache/source['archive'];public_download('Shashanksaraswat123939/mysim-cpu-benchmark','inputs-v1',source['archive'],archive)
 with zipfile.ZipFile(archive) as z:data=z.read('source.fbx')
 assert hashlib.sha256(data).hexdigest()==source['sha256'];fbx=cache/'source.fbx';fbx.write_bytes(data);del data;import_patch.install();bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(fbx),use_anim=False);obj=bpy.context.scene.objects.get(recipe['mesh']);assert obj and obj.type=='MESH';assert len(obj.data.vertices)==recipe['specification']['vertices'];before=fingerprint(obj);matrix=obj.matrix_world.copy();normalmatrix=matrix.to_3x3().inverted().transposed();mesh=obj.data;mesh.calc_loop_triangles();adj={i:set() for i in range(len(mesh.vertices))}
 for edge in mesh.edges:
  a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
 todo=set(adj);components=[]
 while todo:
  seed=min(todo);todo.remove(seed);stack=[seed];members=[]
  while stack:
   v=stack.pop();members.append(v)
   for n in adj[v]:
    if n in todo:todo.remove(n);stack.append(n)
  selected=set(members);faces=[p for p in mesh.polygons if set(p.vertices)<=selected];points=[matrix@mesh.vertices[i].co for i in members];local=[mesh.vertices[i].co for i in members];centre=sum(points,Vector())/max(1,len(points));normalgroups={}
  for face in faces:
   n=(normalmatrix@face.normal).normalized();key=tuple(round(x,4) for x in n);normalgroups.setdefault(str(key),[]).append(face.index)
  components.append(dict(component_root=seed,vertices=members,polygons=[p.index for p in faces],bounds_local=[[min(p[a] for p in local) for a in range(3)],[max(p[a] for p in local) for a in range(3)]],bounds_world=[[min(p[a] for p in points) for a in range(3)],[max(p[a] for p in points) for a in range(3)]],centroid_world=list(centre),normal_groups=normalgroups))
 polygons=[]
 for p in mesh.polygons:
  points=[matrix@mesh.vertices[i].co for i in p.vertices];normal=(normalmatrix@p.normal).normalized();area=sum((points[i]-points[0]).cross(points[i+1]-points[0]).length*.5 for i in range(1,len(points)-1));uv={layer.name:[list(layer.data[i].uv) for i in p.loop_indices] for layer in mesh.uv_layers};polygons.append(dict(polygon=p.index,vertices=list(p.vertices),loop_indices=list(p.loop_indices),area_world=area,normal_world=list(normal),material_index=p.material_index,uv=uv))
 mesh.update();dominant=max(mesh.polygons,key=lambda p:p.area);normal=(normalmatrix@dominant.normal).normalized();obj['drain_source_normal_world']=list(normal)
 obj.data.materials.clear()
 for m in recipe['material_bindings']:obj.data.materials.append(make_material(m,r/'wave-input',recipe['category']))
 images=render_review(obj,[],out/recipe['procedure_id']);assert fingerprint(obj)==before,'Source positions/topology/UV/world placement changed during design study'
 anatomy=dict(procedure_id=recipe['procedure_id'],mesh=recipe['mesh'],source_sha256=source['sha256'],source_fingerprint=before,vertices_local=[list(v.co) for v in mesh.vertices],world_matrix=[list(row) for row in matrix],components=components,polygons=polygons,material_bindings=recipe['material_bindings'],design_questions=job['design_questions'],no_world_unit_claim=True,source_geometry_unchanged=True)
 anatomy_path=out/(recipe['procedure_id']+'-feature-anatomy.json');anatomy_path.write_text(json.dumps(anatomy,indent=2));report.update(state='COMPLETE_DESIGN_EVIDENCE',processed=1,records=[dict(procedure_id=recipe['procedure_id'],mesh=recipe['mesh'],feature_anatomy=anatomy_path.name,images=[Path(x).name for x in images],source_geometry_unchanged=True,source_fingerprint=before,component_count=len(components),automated_checks_passed=True,scope='source_feature_design_study',geometry_upgrade=False,semantic_operator_implemented=False)])
except Exception as error:
 report.update(state='DESIGN_STUDY_FAILED',failed=1,failures=[dict(procedure_id=recipe['procedure_id'],error=str(error))])
report.update(elapsed_seconds=round(time.monotonic()-start,2),peak_RSS_MiB=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1),updated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()));assert report['peak_RSS_MiB']<12288 and report['elapsed_seconds']<270*60;(out/(ident+'-checkpoint.json')).write_text(json.dumps(report,indent=2));hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()};(out/'SHA256SUMS.json').write_text(json.dumps(hashes));archive=r/(ident+'-'+os.environ['GITHUB_RUN_ID']+'.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
 for p in out.iterdir():z.write(p,p.name)
assert archive.stat().st_size<1024**3;result=release_upload(['gh','release','upload',tag,str(archive),'--repo',os.environ['GITHUB_REPOSITORY'],'--clobber'],mandatory=True);assert result.returncode==0,'Design evidence publication failed'
if report['failed']:raise RuntimeError(report['failures'][0]['error'])
