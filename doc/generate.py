#############################################################################
# This Python file uses the following encoding: utf-8                       #
#############################################################################
# Copyright (C) 2016 Laboratório de Sistemas e Tecnologia Subaquática       #
# Departamento de Engenharia Electrotécnica e de Computadores               #
# Rua Dr. Roberto Frias, 4200-465 Porto, Portugal                           #
#############################################################################
# Author: Ricardo Martins                                                   #
#############################################################################

import sys
import os
import os.path
import shutil
import rst
import message
import argparse
import subprocess
import json
from subprocess import check_call
import re

# Folder where this script is located.
cod_dir = os.path.dirname(os.path.abspath(__file__))

# Parse command line arguments.
parser = argparse.ArgumentParser(
    description="This script generates IMC's reference documentation.")
parser.add_argument('--prefix', dest='prefix', default=os.path.join(cod_dir, 'reference'),
    help='destination folder')
parser.add_argument('--commit', dest='commit', default='unknown',
    help='commit id')
parser.add_argument('--build-versions', dest='build_versions', action='store_true',
    help='build documentation for all versions (tags)')
args = parser.parse_args()

def generate_docs(outdir, xml_file, commit_id):
    """Generate documentation for a specific version"""
    # Destination/build folder for this version
    bld_dir = outdir
    src_dir = os.path.join(bld_dir, '_sources')
    thm_dir = os.path.join(cod_dir, 'themes')
    img_dir = os.path.join(cod_dir, 'images')

    # Parse XML
    from xml.etree.ElementTree import ElementTree
    tree = ElementTree()
    root = tree.parse(xml_file)
    release = root.get('version')
    version = '.'.join(release.split('.')[:2])
    revision = commit_id

    files = []

    # Prepare directory tree.
    shutil.rmtree(src_dir, True)
    os.makedirs(src_dir)
    shutil.copytree(img_dir, os.path.join(bld_dir, 'images'))

    # Message format.
    text = rst.h1('Message Format')
    files.append('Message Format.rst')

    # Field types.
    text += rst.h2('Field types')
    text += rst.block(root.find('types/description').text)
    ttypes = rst.Table()
    ttypes.add_row('Name', 'Size', 'Description')
    for t in root.findall('types/type'):
        if 'size' in t.attrib:
            size = t.attrib['size'].strip()
        else:
            size = 'n/a'
        ttypes.add_row(t.attrib['name'], size, t.find('description').text)
    text += str(ttypes)
    open(os.path.join(src_dir, 'Message Format.rst'), 'w').write(text)

    # Serialization.
    text = rst.h2('Serialization')
    text += rst.block(root.find('serialization/description').text)
    ttypes = rst.Table()
    ttypes.add_row('Name', 'Serialization')
    for t in root.findall('serialization/type'):
        ttypes.add_row(t.attrib['name'], t.find('description').text)
    text += str(ttypes)
    open(os.path.join(src_dir, 'Message Format.rst'), 'a').write(text)

    # Header.
    text = rst.h2('Header')
    text += rst.block(root.find('header/description').text)
    table = rst.Table()
    table.add_row('Name', 'Type', 'Fixed Value', 'Description')
    for t in root.findall('header/field'):
        if 'value' in t.attrib:
            value = t.attrib['value']
        else:
            value = '-'
        table.add_row(t.attrib['name'] + '\n(*' + t.attrib['abbrev'] + '*)', t.attrib['type'], value,
                    t.find('description').text)
    text += str(table)
    open(os.path.join(src_dir, 'Message Format.rst'), 'a').write(text)

    # Footer.
    text = rst.h2('Footer')
    text += rst.block(root.find('footer/description').text)
    table = rst.Table()
    table.add_row('Name', 'Type', 'Fixed Value', 'Description')
    for t in root.findall('footer/field'):
        if 'value' in t.attrib:
            value = t.attrib['value']
        else:
            value = '-'
        table.add_row(t.attrib['name'] + '\n(*' + t.attrib['abbrev'] + '*)', t.attrib['type'], value,
                    t.find('description').text)
    text += str(table)
    open(os.path.join(src_dir, 'Message Format.rst'), 'a').write(text)

    # Units.
    text = rst.h2('Reference of Units')
    text += rst.block(root.find('units/description').text)
    tunits = rst.Table()
    tunits.add_row('Abbreviation', 'Name')
    for u in root.findall('units/unit'):
        tunits.add_row(u.attrib['abbrev'], u.attrib['name'])
    text += str(tunits)
    open(os.path.join(src_dir, 'Message Format.rst'), 'a').write(text)

    # Messages by Category.
    categories = []
    for g in root.findall('message'):
        # Handle missing 'category' attribute in older IMC versions
        if 'category' in g.attrib:
            categories.append(g.attrib['category'])
        else:
            # Use 'Core' as default category if not specified
            categories.append('Core')
    categories = sorted(set(categories), key=lambda x: categories.index(x))

    for name in categories:
        files.append(name + '.rst')
        text = rst.h1(name + ' Messages')
        open(os.path.join(src_dir, name + '.rst'), 'w').write(text)

    # Messages.
    for msg in root.findall('message'):
        abbrev = msg.attrib['abbrev']
        id = int(msg.attrib['id'])

        text = '.. _%s:\n\n' % msg.get('abbrev')
        text += rst.h2(msg.attrib['name'])

        if msg.find('description') is None:
            text += rst.block('No description')
        elif msg.find('description').text is None:
            text += rst.block('No description')
        elif msg.find('description').text.strip() == '':
            text += rst.block('No description')
        elif msg.find('description').text.strip() != '':
            text += rst.block(msg.find('description').text)

        text += '- Abbreviation: ' + abbrev + '\n'
        text += '- Identification Number: ' + msg.attrib['id'] + '\n'
        text += '- Fixed Payload Size: ' + str(message.get_fixed_size(msg)) + '\n'
        text += '\n'

        if msg.findall('field') == []:
            text += 'This message has no fields.\n\n'
        else:
            t = rst.Table()
            t.add_row('Name', 'Abbreviation', 'Unit', 'Type', 'Description', 'Range')
            for f in msg.findall('field'):
                if f.find('description') is None:
                    desc = ''
                else:
                    desc = f.find('description').text

                unit = '-'
                if 'unit' in f.attrib:
                    unit = f.attrib['unit'].strip()

                frange = 'Same as field type'

                name = f.attrib['name'].strip()
                t.add_row(name, f.attrib['abbrev'], '*' + unit + '*', f.attrib['type'], desc, frange)
            text += str(t)

        # Handle missing 'category' attribute in older IMC versions
        if 'category' in msg.attrib:
            category = msg.attrib['category']
        else:
            category = 'Core'  # Default category if not specified

        open(os.path.join(src_dir, category + '.rst'), 'a').write(text)

    # Master document.
    fd = open(os.path.join(src_dir, 'index.rst'), 'w')
    fd.write(rst.h1('IMC v%s-%s' % (release, revision)))
    fd.write('\n')

    fd.write(rst.block(root.find('description').text))

    fd.write('''
.. toctree::
   :maxdepth: 2

''')

    for f in files:
        fd.write('   ' + f + '\n')
    fd.close()

    # Build the documentation
    subprocess.check_call(['sphinx-build',
                       '-b', 'html',
                       '-E',
                       '-d', os.path.join(bld_dir, 'doctree'),
                       '-c', cod_dir,
                       '-D', 'version=' + version,
                       '-D', 'release=' + release,
                       '-D', 'html_title=' + 'IMC v' + release + ' Specification',
                       src_dir,
                       bld_dir
                       ])
    
    return {"version": version, "release": release}

def parse_version(version_str):
    """Parse version string to a tuple of integers for proper comparison"""
    # Extract version numbers from formats like "v5.4.19" or "Current (5.4.19)"
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', version_str)
    if match:
        return tuple(map(int, match.groups()))
    return (0, 0, 0)  # Default for versions that can't be parsed

def inject_version_selector(directory, versions_data, current_version):
    """Add version selector to all HTML files in the directory"""
    # Create versions dropdown HTML
    versions_html = """
    <div class="sidebar-block">
      <div class="sidebar-wrapper">
        <h2>Versions</h2>
        <div class="versions">
          <div class="version-select-container">
            <select class="version-select" onchange="window.location.href=this.value">
    """
    
    # Add options for each version
    for ver in versions_data:
        selected = "selected" if ver["version_id"] == current_version else ""
        versions_html += f"""        <option value="../{ver["version_id"]}/index.html" {selected}>{ver["display_name"]}</option>\n"""
    
    versions_html += """
            </select>
          </div>
        </div>
      </div>
    </div>
    <style>
      .version-select-container {
        padding: 5px;
      }
      .version-select {
        width: 100%;
        padding: 5px;
        border: 1px solid #ccc;
        border-radius: 3px;
      }
    </style>
    """
    
    # Find all HTML files in the directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".html"):
                filepath = os.path.join(root, file)
                with open(filepath, "r") as f:
                    content = f.read()
                
                # Insert version selector into the sidebar
                if '<div class="sphinxsidebar">' in content:
                    content = content.replace(
                        '<div class="sphinxsidebar">',
                        '<div class="sphinxsidebar">' + versions_html
                    )
                    
                    # Write the modified content back
                    with open(filepath, "w") as f:
                        f.write(content)

# Main documentation build and version selection logic
if args.build_versions:
    # Get git tags
    result = subprocess.run(['git', 'tag'], stdout=subprocess.PIPE, text=True)
    tags = result.stdout.strip().split('\n')
    
    # For simplicity, we'll use the current repo and just build docs for different tags
    versions_data = []
    
    # Ensure the main reference directory exists
    shutil.rmtree(args.prefix, True)
    os.makedirs(args.prefix, exist_ok=True)
    
    # Build documentation for the current version first
    print("Building current version...")
    current_dir = os.path.join(args.prefix, "current")
    os.makedirs(current_dir, exist_ok=True)
    current_info = generate_docs(current_dir, os.path.join(cod_dir, '..', 'IMC.xml'), "current")
    
    versions_data.append({
        "version_id": "current", 
        "display_name": f"Current ({current_info['release']})",
        "info": current_info
    })
    
    # Build documentation for each tag
    for tag in tags:
        if tag.strip():  # Skip empty tags
            print(f"Building documentation for tag: {tag}")
            # Create output directory for this version
            version_dir = os.path.join(args.prefix, tag)
            os.makedirs(version_dir, exist_ok=True)
            
            try:
                # Checkout the tag to get the XML file
                subprocess.check_call(['git', 'checkout', tag, '--', '../IMC.xml'], cwd=cod_dir)
                
                # Generate documentation for this version
                version_info = generate_docs(version_dir, os.path.join(cod_dir, '..', 'IMC.xml'), tag)
                
                versions_data.append({
                    "version_id": tag, 
                    "display_name": f"v{version_info['release']}",
                    "info": version_info
                })
            except Exception as e:
                print(f"Error building documentation for {tag}: {e}")
            finally:
                # Restore the original file
                subprocess.check_call(['git', 'checkout', 'HEAD', '--', '../IMC.xml'], cwd=cod_dir)
    
    # Sort versions by semantic versioning (newest first)
    versions_data.sort(key=lambda x: parse_version(x["display_name"]), reverse=True)
    
    # Keep "Current" at the top of the list regardless of version number
    current_version = next((v for v in versions_data if v["version_id"] == "current"), None)
    if current_version:
        versions_data.remove(current_version)
        versions_data.insert(0, current_version)
    
    # Inject version selector into all HTML files
    for version in versions_data:
        inject_version_selector(
            os.path.join(args.prefix, version["version_id"]), 
            versions_data, 
            version["version_id"]
        )
    
    # Create a main index.html that redirects to the current version
    with open(os.path.join(args.prefix, 'index.html'), 'w') as index:
        index.write('''
<!DOCTYPE html>
<html>
  <head>
    <meta http-equiv="refresh" content="0; url=./current/index.html" />
    <title>IMC Documentation</title>
  </head>
  <body>
    <p>Redirecting to latest documentation...</p>
    <p>If you are not redirected automatically, follow this <a href="./current/index.html">link</a>.</p>
  </body>
</html>
''')

    print("Documentation built for all versions with version selector.")
else:
    # Standard single-version build
    # Prepare directory tree
    bld_dir = args.prefix
    shutil.rmtree(bld_dir, True)
    os.makedirs(bld_dir, exist_ok=True)
    
    # Generate documentation for current version
    generate_docs(bld_dir, os.path.join(cod_dir, '..', 'IMC.xml'), args.commit)
