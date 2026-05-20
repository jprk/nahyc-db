import zipfile
import xml.etree.ElementTree as ET
import sys

def read_docx(file_path):
    try:
        with zipfile.ZipFile(file_path) as docx:
            xml_content = docx.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            paragraphs = tree.findall('.//w:p', ns)
            text = []
            for p in paragraphs:
                texts = p.findall('.//w:t', ns)
                if texts:
                    text.append(''.join(t.text for t in texts))
            return '\n'.join(text)
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    print(read_docx(sys.argv[1]))
