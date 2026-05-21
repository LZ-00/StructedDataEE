# -*- coding: utf-8 -*-
import zipfile
import re
import os
import shutil
from xml.etree import ElementTree as ET

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'}

def read_docx_structure(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml')
        rels_xml = z.read('word/_rels/document.xml.rels')
    
    rels_root = ET.fromstring(rels_xml)
    rel_ns = 'http://schemas.openxmlformats.org/package/2006/relationships'
    rel_map = {}
    for rel in rels_root:
        rid = rel.get('Id')
        target = rel.get('Target')
        rel_map[rid] = target
    
    root = ET.fromstring(xml)
    w_ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    a_ns = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
    r_ns = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
    
    items = []
    img_idx = 0
    for p in root.iter(f'{w_ns}p'):
        parts = []
        for child in p:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag == 'r':
                for t in child.iter(f'{w_ns}t'):
                    if t.text:
                        parts.append(t.text)
                    if t.tail:
                        parts.append(t.tail)
            elif tag == 'drawing' or tag == 'pict':
                # find blip embed
                for blip in child.iter(f'{a_ns}blip'):
                    embed = blip.get(f'{r_ns}embed')
                    if embed and embed in rel_map:
                        img_idx += 1
                        items.append(('IMAGE', embed, rel_map[embed], img_idx))
        line = ''.join(parts).strip()
        if line:
            items.append(('TEXT', line))
    
    return items, rel_map

def extract_images(path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.startswith('word/media/'):
                fname = os.path.basename(name).strip()
                if not fname:
                    continue
                with z.open(name) as src, open(os.path.join(out_dir, fname), 'wb') as dst:
                    dst.write(src.read())

def dump_doc(path, label, img_dir=None):
    print(f'\n{"="*60}\n{label}\n{"="*60}')
    items, rel_map = read_docx_structure(path)
    if img_dir:
        extract_images(path, img_dir)
    for item in items:
        if item[0] == 'TEXT':
            print(f'T: {item[1]}')
        else:
            print(f'I: [{item[3]}] {item[2]} -> {rel_map.get(item[1], item[2])}')

p1 = r'e:\研\lab106\软著\激光焊接全流程数据库管理系统\2-激光焊接全流程数据库管理系统操作手册--V1.docx'
p2 = r'e:\研\lab106\软著\激光焊接结构化数据抽取与质量评估系统\激光焊接结构化数据抽取与质量评估系统.docx'
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docx_extract')
os.makedirs(out, exist_ok=True)

def write_dump(path, label, img_subdir, txt_name):
    items, rel_map = read_docx_structure(path)
    img_dir = os.path.join(out, img_subdir)
    extract_images(path, img_dir)
    with open(os.path.join(out, txt_name), 'w', encoding='utf-8') as f:
        f.write(f'{"="*60}\n{label}\n{"="*60}\n')
        for item in items:
            if item[0] == 'TEXT':
                f.write(f'T: {item[1]}\n')
            else:
                f.write(f'I: [{item[3]}] {item[2]}\n')

write_dump(p1, '手册1-参考', 'ref_images', 'manual1.txt')
write_dump(p2, '手册2-本系统', 'sys_images', 'manual2.txt')
print('Done', out)
