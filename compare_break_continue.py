"""比较break/continue节点在output和target中的连接"""
import json

with open('output_flowchart.json', 'r', encoding='utf-8') as f:
    output = json.load(f)

with open('target.json', 'r', encoding='utf-8') as f:
    target = json.load(f)

# 查找包含break或continue的节点
break_continue_nodes = []
for node in output['items']:
    text = node.get('text', '').lower()
    if text == 'break;' or text == 'continue;':
        break_continue_nodes.append(node['id'])

print(f"发现{len(break_continue_nodes)}个break/continue节点\n")

for node_id in break_continue_nodes:
    # 找到对应的节点
    output_node = next((n for n in output['items'] if n['id'] == node_id), None)
    target_node = next((n for n in target['items'] if n['id'] == node_id), None)
    
    if not output_node:
        continue
    
    suffix = node_id.split('_')[-1]
    print(f"="*60)
    print(f"节点_{suffix}: {output_node['text']}")
    print(f"="*60)
    
    # Output的连接
    output_conns = [c for c in output['connections'] if c['start_item_id'] == node_id]
    print(f"Output的出站连接（{len(output_conns)}个）:")
    for c in output_conns:
        end_suffix = c['end_item_id'].split('_')[-1]
        print(f"  {c['start_point_type']} -> _{end_suffix}")
    
    # Target的连接
    if target_node:
        target_conns = [c for c in target['connections'] if c['start_item_id'] == node_id]
        print(f"Target的出站连接（{len(target_conns)}个）:")
        for c in target_conns:
            end_suffix = c['end_item_id'].split('_')[-1]
            print(f"  {c['start_point_type']} -> _{end_suffix}")
    else:
        print("Target中没有此节点")
    
    print()

