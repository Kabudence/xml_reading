import time
import xml.etree.ElementTree as ET
import json

import pytz
import requests  # Importa requests para realizar llamadas HTTP
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import jwt
from datetime import datetime, timezone, timedelta

# Rutas a las carpetas que quieres monitorear
folder_paths = [
    r"C:\Users\USER\Documents\TESTEOXML"

]
# folder_paths = [
#     r"D:\SainfoNet_FE_Rafael\XMLData",
#     r"D:\SainfoNet_FE_katherine\XMLData",
#     r"D:\SainfoNet_FE_hidalgo\XMLData"
#
# ]

# Endpoints de tus APIs
ENDPOINT_CREATE_CLIENT = "https://salesmanagerproject-production.up.railway.app/api/clientes/automatic-create"
ENDPOINT_CREATE_INPROCESS = "https://salesmanagerproject-production.up.railway.app/api/regmovcab/create-inprocess"
ENDPOINT_CANCEL="https://salesmanagerproject-production.up.railway.app/api/regmovcab/cancel-sale/"


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
        'sac': 'urn:sunat:names:specification:ubl:peru:schema:xsd:SunatAggregateComponents-1'

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

        # Extraer información de "NoteSalesInformation"
        note_sales_info = root.find('.//cbc:ID', namespaces)
        # Si es un Resumen de Bajas (RC)
        if note_sales_info is not None and note_sales_info.text.startswith("RC"):
            token = create_jwt_token()
            headers = {'Authorization': f'Bearer {token}'}

            # Buscar TODAS las líneas de resumen
            summary_lines = root.findall('.//sac:SummaryDocumentsLine', namespaces)

            for line in summary_lines:
                num_docum_element = line.find('.//cbc:ID', namespaces)
                if num_docum_element is not None:
                    num_docum = num_docum_element.text.strip()  # Elimina espacios antes/después
                    print("num_docum encontrado:", num_docum)

                    cancel_url = f"{ENDPOINT_CANCEL}{num_docum}"
                    response = requests.put(cancel_url, headers=headers)
                    print(f"Cancelando RC - {num_docum}: {response.status_code} - {response.text}")

            return None

        # Si es una Anulación (RA)
        if note_sales_info is not None and note_sales_info.text.startswith("RA"):
            serial = root.find('.//sac:DocumentSerialID', namespaces)
            number = root.find('.//sac:DocumentNumberID', namespaces)
            if serial is not None and number is not None:
                num_docum = f"{serial.text}-{number.text}"
                print("num_docum encontrado:", num_docum)
                token = create_jwt_token()  # Generar token JWT
                headers = {'Authorization': f'Bearer {token}'}
                cancel_url = f"{ENDPOINT_CANCEL}{num_docum}"
                response = requests.put(cancel_url, headers=headers)
                print(f"Cancelando documento RA {num_docum}: {response.status_code} - {response.text}")
            return None  # No procesar como venta normal


        issue_date = root.find('.//cbc:IssueDate', namespaces)

        note_sales_info_obj = NoteSalesInformation(
            note_sales_info.text if note_sales_info is not None else None,
            issue_date.text if issue_date is not None else None
        )

        # Extraer "ItemList"
        item_list = []
        invoice_lines = root.findall('.//cac:InvoiceLine', namespaces)
        for invoice_line in invoice_lines:
            # Buscar la descripción del artículo en <cac:Item>
            item_name = invoice_line.find('.//cac:Item/cbc:Description', namespaces)
            item_name = item_name.text if item_name is not None else None

            # Buscar la cantidad dentro de <cac:InvoiceLine>
            item_quantity = invoice_line.find('.//cbc:InvoicedQuantity', namespaces)
            item_quantity = item_quantity.text if item_quantity is not None else None

            # Buscar el precio base (sin IGV) y aplicar ajustes
            item_price_element = invoice_line.find('.//cbc:LineExtensionAmount', namespaces)
            if item_price_element is not None:
                # Paso 1: Obtener el precio base del XML
                precio_base = float(item_price_element.text)

                # Paso 2: Si el nombre termina en '*', quitar el 5%
                if item_name and item_name.endswith('*'):
                    precio_base = precio_base / 1.05  # 🔄 Quitar el 5% adicional
                    item_name = item_name.rstrip('*')  # 🧹 Eliminar el asterisco

                # Paso 3: Calcular el precio con IGV (18%)
                item_price = round(precio_base * 1.18, 2)  # 💡 Precio final con IGV
            else:
                item_price = None

            item_obj = Item(item_name, item_quantity, item_price)
            item_list.append(item_obj.to_dict())

        result = {
            "MyInformation": my_info.to_dict(),
            "PartyClient": party_client.to_dict(),
            "OperationInformation": operation_info.to_dict(),
            "ItemList": item_list,
            "NoteSalesInformation": note_sales_info_obj.to_dict()
        }

        return json.dumps(result, indent=4, ensure_ascii=False)

    except Exception as e:
        print(f"Error al procesar el XML: {e}")
        return None


class XMLHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.xml'):
            print(f"Nuevo archivo XML detectado: {event.src_path}")
            with open(event.src_path, 'r', encoding='utf-8', errors='replace') as file:
                content = file.read()
                json_str = process_xml(content)
                if json_str:
                    json_data = json.loads(json_str)
                    print("Contenido en formato JSON:")
                    print(json.dumps(json_data, indent=4, ensure_ascii=False))

                    # Generar token JWT
                    token = create_jwt_token()
                    headers = {'Authorization': f'Bearer {token}'}

                    # Payload para el endpoint '/automatic-create'
                    payload_automatic = {
                        "PartyClient": json_data.get("PartyClient")
                    }
                    print("Payload para /automatic-create:")
                    print(json.dumps(payload_automatic, indent=4, ensure_ascii=False))
                    response_cliente = requests.post(ENDPOINT_CREATE_CLIENT, json=payload_automatic, headers=headers)
                    print(f"Respuesta de /automatic-create: {response_cliente.json()}")

                    # Procesar NoteSalesInformation para obtener tip_docum
                    note_sales = json_data.get("NoteSalesInformation", {})
                    note_id = note_sales.get("NoteID", "")
                    print("NOTE ID =",note_id)
                    if note_id.startswith("F001"):
                        tip_docum = "01"
                    elif note_id.startswith("B001"):
                        tip_docum = "02"
                    else:
                        tip_docum = "00"

                    # Calcular 'idemp' en función del IdentifyCode y, si corresponde, de los primeros 4 dígitos de NoteID
                    identify_code = json_data.get("MyInformation", {}).get("IdentifyCode", "")
                    print("codigo de identificacion:",identify_code)
                    if identify_code == "10412942987":
                        idemp = "01"
                    elif identify_code == "10179018913":
                        idemp = "04"
                    elif identify_code == "20481678880":
                        if note_id.startswith("B001") or note_id.startswith("F001"):
                            idemp = "02"
                        elif note_id.startswith("B002") or note_id.startswith("F002"):
                            idemp = "03"
                        elif note_id.startswith("B003") or note_id.startswith("F003"):
                            idemp = "05"
                        else:
                            idemp = "01"  # Valor por defecto si no coincide
                    else:
                        idemp = "06"

                    print("EL IDEMP ES: ",idemp)
                    # Payload para el endpoint '/regmovcab/create-inprocess'
                    op_info = json_data.get("OperationInformation", {})
                    payload_regmovcab = {
                        "tip_mov": 1,  # Valor de ejemplo (convertido a num en el endpoint)
                        "tip_vta": "01",  # Valor fijo
                        "tip_docum": tip_docum,  # Calculado a partir de NoteSalesInformation.NoteID
                        "num_docum": note_id,  # NoteID
                        "ruc_cliente": identify_code,
                        "vendedor": None,  # Por defecto NULL
                        "vvta": float(op_info.get("Amount", 0)),
                        "igv": float(op_info.get("IGV", 0)),
                        "total": float(op_info.get("TotalAmount", 0)),
                        "idemp": idemp,
                        "estado": 2,  # Valor fijo
                        "ItemList": json_data.get("ItemList", [])
                    }

                    print("Payload para /regmovcab/create-inprocess:")
                    print(json.dumps(payload_regmovcab, indent=4, ensure_ascii=False))
                    response_regmovcab = requests.post(ENDPOINT_CREATE_INPROCESS, json=payload_regmovcab, headers=headers)
                    print(f"Respuesta de /regmovcab/create-inprocess: {response_regmovcab.json()}")


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


def create_jwt_token():
    secret_key = "a25fc7905471e60a094749de707ab956871d5ba26df167a03863911a70c54950"  # Debe coincidir con tu configuración en la API
    peru_tz = pytz.timezone('America/Lima')  # Zona horaria de Perú
    now = datetime.now(peru_tz)  # Hora actual en Perú
    payload = {
        "exp": now + timedelta(minutes=60),
        "iat": now,
        "sub": "xml_monitor"  # Identificador para este cliente (opcional)
    }
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token

if __name__ == "__main__":
    start_monitoring()
