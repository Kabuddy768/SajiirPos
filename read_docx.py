import zipfile
import xml.etree.ElementTree as ET
import sys

def read_docx(file_path):
    try:
        z = zipfile.ZipFile(file_path)
        xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        texts = []
        for node in tree.iterfind('.//w:t', namespace):
            if node.text:
                texts.append(node.text)
        
        with open('plan.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(texts))
        print("Successfully written to plan.txt")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    read_docx(sys.argv[1])
