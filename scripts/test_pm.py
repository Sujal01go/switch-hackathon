from src.project_manager import ProjectManager

pm = ProjectManager()
print('Active project:', pm.active_project)
projs = pm.list_projects()
print('Found projects count:', len(projs))
for p in projs[:6]:
    print(f"  {p['name']} -> {p['type']}")

ok, msg, path = pm.set_active_project('portfolio')
print('Switch test:', ok, msg, path)
assert ok is True
assert pm.active_project.name == 'portfolio'

target, clean = pm.extract_target_project_from_text('in ARS-Module: fix the database connection')
print('Extraction test:', target, '| clean text:', clean)
assert target is not None and target.name == 'ARS-Module'
assert clean == 'fix the database connection'

# Reset active project to sample_repo for baseline
pm.set_active_project('sample_repo')
print('ProjectManager verification SUCCESSFUL!')

