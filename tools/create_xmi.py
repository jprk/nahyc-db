# Vytvoření XMI souboru pro import do Enterprise Architect

xmi_ns = "http://schema.omg.org/spec/XMI/2.1"
uml_ns = "http://schema.omg.org/spec/UML/2.1"
import os

# Definice kořenového elementu
xmi = etree.Element("{%s}XMI" % xmi_ns, nsmap={"xmi": xmi_ns, "uml": uml_ns})
uml_model = etree.SubElement(xmi, "{%s}Model" % uml_ns, {"name": "RegulatoryDocumentsDB"})

# Definice UML tříd a atributů
classes = {
    "Document": [("id", "Integer"), ("title", "String"), ("description", "String"), ("type_id", "Integer"),
                 ("source", "String"), ("file_path", "String"), ("version", "Integer"), ("created_at", "DateTime"),
                 ("updated_at", "DateTime")],
    "DocumentVersion": [("id", "Integer"), ("document_id", "Integer"), ("version", "Integer"), ("file_path", "String"),
                        ("change_log", "String"), ("created_at", "DateTime")],
    "DocumentType": [("id", "Integer"), ("name", "String"), ("description", "String")],
    "Keyword": [("id", "Integer"), ("keyword", "String")],
    "DocumentKeyword": [("document_id", "Integer"), ("keyword_id", "Integer")],
    "DocumentSource": [("id", "Integer"), ("name", "String")]
}

uml_classes = {}
for class_name, attributes in classes.items():
    uml_class = etree.SubElement(uml_model, "{%s}Class" % uml_ns, {"name": class_name})
    uml_classes[class_name] = uml_class
    for attr_name, attr_type in attributes:
        etree.SubElement(uml_class, "{%s}Property" % uml_ns, {"name": attr_name, "type": attr_type})

# Vztahy mezi třídami
relations = [
    ("DocumentVersion", "Document", "document_id", "1", "M"),
    ("Document", "DocumentType", "type_id", "M", "1"),
    ("DocumentKeyword", "Document", "document_id", "M", "1"),
    ("DocumentKeyword", "Keyword", "keyword_id", "M", "1"),
    ("Document", "DocumentSource", "source", "M", "1")
]

for source, target, attr, src_mult, tgt_mult in relations:
    relation = etree.SubElement(uml_model, "{%s}Association" % uml_ns, {"name": f"{source}_{target}"})
    etree.SubElement(relation, "{%s}OwnedEnd" % uml_ns, {"type": source, "multiplicity": src_mult})
    etree.SubElement(relation, "{%s}OwnedEnd" % uml_ns, {"type": target, "multiplicity": tgt_mult})

# Uložení XMI souboru
xmi_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db', 'RegulatoryDocumentsDB.xmi')
with open(xmi_file_path, "wb") as f:
    f.write(etree.tostring(xmi, pretty_print=True, xml_declaration=True, encoding="UTF-8"))

# Vrácení cesty k souboru
xmi_file_path
