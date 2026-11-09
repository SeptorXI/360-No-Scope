"""Keep the class Ability4/H action free; reload guns through native Use/F."""
import json

def apply(pack):
    def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
    def write(path, data): path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    profiles=read(pack/'ranger-snipers-reload-profiles.json')['Profiles']
    changed=[]
    for profile in profiles:
        weapon=profile['WeaponId'];slug=weapon.removeprefix('Weapon_Crossbow_')
        paths=list((pack/'Server/Item/Items').rglob(weapon+'.json'))
        assert len(paths)==1, weapon+' item is ambiguous'
        path=paths[0];item=read(path);mapping=item['Interactions']
        root='Root_RS_'+slug+'_Reload'
        assert mapping.pop('Ability4')==root and 'Use' not in mapping, weapon+' unexpected input mappings'
        mapping['Use']=root;write(path,item);changed.append(path.relative_to(pack).as_posix())
        for path in (pack/'Server/Item/RootInteractions/RangerSnipers').glob('Root_RS_'+slug+'_*.json'):
            data=read(path);before=json.dumps(data,sort_keys=True)
            def visit(node):
                if isinstance(node,dict):
                    rules=node.get('Rules',{})
                    for key,values in rules.items():
                        if isinstance(values,list):
                            values=list(dict.fromkeys('Use' if v=='Ability4' else v for v in values))
                            if '_Reload' in path.stem and key=='BlockedBy':values=[v for v in values if v!='Use']
                            rules[key]=values
                    for value in node.values():visit(value)
                elif isinstance(node,list):
                    for value in node:visit(value)
            visit(data)
            if path.stem==root:
                begin=data['Interactions'][0]
                assert begin['Type']=='RSChamber' and begin['Operation']=='BeginReload'
                # Keep native world interactions before the weapon fallback.
                data['Interactions'][0]={'Type':'UseBlock','Failed':{'Type':'UseEntity','Failed':begin}}
            if json.dumps(data,sort_keys=True)!=before:
                write(path,data);changed.append(path.relative_to(pack).as_posix())
    language=pack/'Server/Languages/en-US/server.lang'
    text=language.read_text(encoding='utf-8').replace('\\nR: reload ', '\\nF: reload ').replace('; R reload ', '; F reload ')
    language.write_text(text,encoding='utf-8')
    return {'action':'Use','defaultKey':'F','classActionPreserved':'Ability4/H','weapons':len(profiles),'changedAssets':sorted(changed)}
