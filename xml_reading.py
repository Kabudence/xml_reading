import time
import xml.etree.ElementTree as ET
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Rutas a las carpetas que quieres monitorear
folder_paths = [
    r"C:\Users\USER\Documents\TESTEOXML"
]


# Definición de clases para representar los datos del XML
class MyInformation:
    def __init__(self, address_type_code, registration_name, identify_code):
        self.address_type_code = address_type_code
        self.registration_name = registration_name
        self.identify_code = identify_code

    def to_dict(self):
        return {
            "AddressTypeCode": self.address_type_code,
            "RegistrationName": self.registration_name,
            "IdentifyCode": self.identify_code
        }


class PartyClient:
    def __init__(self, address_type_code, registration_name, identify_code):
        self.address_type_code = address_type_code
        self.registration_name = registration_name
        self.identify_code = identify_code

    def to_dict(self):
        return {
            "AddressTypeCode": self.address_type_code,
            "RegistrationName": self.registration_name,
            "IdentifyCode": self.identify_code
        }


class Item:
    def __init__(self, item_name, item_quantity, item_price):
        self.item_name = item_name
        self.item_quantity = item_quantity
        self.item_price = item_price

    def to_dict(self):
        return {
            "ItemName": self.item_name,
            "ItemQuantity": self.item_quantity,
            "ItemPrice": self.item_price
        }


class OperationInformation:
    def __init__(self, total_amount, igv, amount, type_operation):
        self.total_amount = total_amount
        self.igv = igv
        self.amount = amount
        self.type_operation = type_operation

    def to_dict(self):
        return {
            "TotalAmount": self.total_amount,
            "IGV": self.igv,
            "Amount": self.amount,
            "TypeOperation": self.type_operation
        }

class NoteSalesInformation:
    def __init__(self, note_id, issue_date):
        self.note_id = note_id
        self.issue_date = issue_date

    def to_dict(self):
        return {
            "NoteID": self.note_id,
            "IssueDate": self.issue_date
        }



# Función para procesar el archivo XML y convertirlo a JSON
def process_xml(xml_content):
    namespaces = {
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    }

    try:
        root = ET.fromstring(xml_content)

        # Extraer información de "MyInformation"
        address_type_code = root.find('.//cbc:AddressTypeCode', namespaces)
        registration_name = root.find('.//cbc:RegistrationName', namespaces)
        identify_code = root.find('.//cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID', namespaces)

        my_info = MyInformation(
            address_type_code.text if address_type_code is not None else None,
            registration_name.text if registration_name is not None else None,
            identify_code.text if identify_code is not None else None
        )

        # Extraer información de "PartyClient"
        client_address_type_code = root.find('.//cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID', namespaces)
        client_registration_name = root.find('.//cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName', namespaces)
        client_identify_code = root.find('.//cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID', namespaces)

        party_client = PartyClient(
            client_address_type_code.text if client_address_type_code is not None else None,
            client_registration_name.text if client_registration_name is not None else None,
            client_identify_code.text if client_identify_code is not None else None
        )

        # Extraer información de "OperationInformation"
        total_amount = root.find('.//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount', namespaces)
        igv = root.find('.//cac:TaxTotal/cbc:TaxAmount', namespaces)
        amount = root.find('.//cac:LegalMonetaryTotal/cbc:LineExtensionAmount', namespaces)
        type_operation = root.find('.//cac:PaymentTerms/cbc:PaymentMeansID', namespaces)

        operation_info = OperationInformation(
            total_amount.text if total_amount is not None else None,
            igv.text if igv is not None else None,
            amount.text if amount is not None else None,
            type_operation.text if type_operation is not None else None
        )

        note_sales_info = root.find('.//cbc:ID', namespaces)
        issue_date = root.find('.//cbc:IssueDate', namespaces)

        note_sales_info_obj = NoteSalesInformation(
            note_sales_info.text if note_sales_info is not None else None,
            issue_date.text if issue_date is not None else None
        )

        # Extraer "ItemList"
        item_list = []

        # Buscar todos los elementos <cac:InvoiceLine> para obtener el precio y la cantidad
        invoice_lines = root.findall('.//cac:InvoiceLine', namespaces)

        for invoice_line in invoice_lines:
            # Buscar la descripción del artículo en <cac:Item>
            item_name = invoice_line.find('.//cac:Item/cbc:Description', namespaces)
            item_name = item_name.text if item_name is not None else None

            # Buscar la cantidad dentro de <cac:InvoiceLine>
            item_quantity = invoice_line.find('.//cbc:InvoicedQuantity', namespaces)
            item_quantity = item_quantity.text if item_quantity is not None else None

            # Buscar el precio dentro de <cac:InvoiceLine>
            item_price = invoice_line.find('.//cbc:LineExtensionAmount', namespaces)
            item_price = item_price.text if item_price is not None else None

            # Crear el objeto Item y agregarlo a la lista
            item_obj = Item(item_name, item_quantity, item_price)
            item_list.append(item_obj.to_dict())

        # El resultado será una lista de diccionarios con los datos de los artículos

        # Crear el resultado final
        result = {
            "MyInformation": my_info.to_dict(),
            "PartyClient": party_client.to_dict(),
            "OperationInformation": operation_info.to_dict(),
            "ItemList": item_list,
            "NoteSalesInformation": note_sales_info_obj.to_dict(),
        }

        return json.dumps(result, indent=4, ensure_ascii=False)

    except Exception as e:
        print(f"Error al procesar el XML: {e}")
        return None


# Clase para manejar eventos de archivos
class XMLHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.xml'):
            print(f"Nuevo archivo XML detectado: {event.src_path}")
            with open(event.src_path, 'r', encoding='utf-8') as file:
                content = file.read()
                json_content = process_xml(content)
                if json_content:
                    print("Contenido en formato JSON:")
                    print(json_content)


# Función principal para monitorear la carpeta
def start_monitoring():
    event_handler = XMLHandler()
    observer = Observer()

    for folder_path in folder_paths:
        observer.schedule(event_handler, folder_path, recursive=True)

    observer.start()
    print("Monitoreando carpeta:", folder_paths)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    start_monitoring()
