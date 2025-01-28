import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ebay import EBaySDK
from threading import Thread
import threading
from concurrent.futures import Future
import json
import xml.etree.ElementTree as ET
import requests
import tkinter
from datetime import datetime, timedelta, UTC

mode = 'PRODUCTION'

API_ENDPOINT = "https://api.sandbox.ebay.com/ws/api.dll" if mode == 'SANDBOX' else "https://api.ebay.com/ws/api.dll"
RESTFUL_API_ENDPOINT = "https://api.sandbox.ebay.com" if mode == 'SANDBOX' else "https://api.ebay.com"
CLIENT_ID = "BambiIve-ListingD-SBX-566ca3cf7-2a51ab02" if mode == 'SANDBOX' else "BambiIve-ListingD-PRD-f66269612-8be4f45b"
DEV_ID = "22ef2f9c-0045-46a9-a008-91cecff74ae1" if mode == 'SANDBOX' else "22ef2f9c-0045-46a9-a008-91cecff74ae1"
CLIENT_SECRET = "SBX-66ca3cf7b186-6b54-42fc-87ea-e283" if mode == 'SANDBOX' else "PRD-662696129406-1233-4c4a-a8e2-afac"
REDIRECT_URI = "Bambi_Iversen-BambiIve-Listin-aarjz" if mode == 'SANDBOX' else "Bambi_Iversen-BambiIve-Listin-akmwwycb"

lock = threading.Lock()

def call_with_future(fn, future, args, kwargs):
    try:
        result = fn(*args, **kwargs)
        future.set_result(result)
    except Exception as exc:
        print(f"Exception occurred in thread: {exc}")  # Print the exception details
        future.set_exception(exc)

def threaded(fn):
    def wrapper(*args, **kwargs):
        future = Future()
        Thread(target=call_with_future, args=(
            fn, future, args, kwargs)).start()
        return future
    return wrapper

class MainWindow(ttkb.Window):
    def __init__(self):
        super().__init__(themename="cosmo")  # Initialize with a theme
        self.title("eBay Listing Duplicator v1.0")
        
        # Create an entry widget with validation for numbers only
        vcmd = (self.register(self.validate_number), '%P')
        self.label = ttkb.Label(self, text="Item ID:")
        self.label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry = ttkb.Entry(self, width=30, validate='key', validatecommand=vcmd)
        self.entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.labelSchedule = ttkb.Label(self, text="Schedule after(min):")
        self.labelSchedule.grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.entrySchedule = ttkb.Entry(self, width=30, validate='key', validatecommand=vcmd)
        self.entrySchedule.grid(row=0, column=3, padx=10, pady=10, sticky="ew")
        self.entrySchedule.insert(0, "120")
        
        # Create a button to open the input dialog
        # self.input_dialog_button = ttkb.Button(self, name="item_id_input", text="Retry Failed Items", command=self.retry_failed_items)
        # self.input_dialog_button.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        
        # Create a button to duplicate text
        self.duplicate_button = ttkb.Button(self, name="duplicate_button", text="Duplicate", command=self.duplicate_text, state=DISABLED)
        self.duplicate_button.grid(row=0, column=4, padx=10, pady=10, sticky="ew")

        self.authorize_button = ttkb.Button(self, name="authorize_button", text="Authorize", command=self.authorize)
        self.authorize_button.grid(row=0, column=5, padx=10, pady=10, sticky="ew")
        
        # Apply styles to make column boundaries clearer
        style = ttkb.Style()
        #style.theme_use("default")  # Use a default theme for customization

        # Configure treeview row and column styles with borderlines
        style.configure(
            "Treeview",
            rowheight=25,
            borderwidth=1,
            relief="solid",  # Adds solid borders for clearer column boundaries
        )
        style.configure(
            "Treeview.Heading",
            borderwidth=1,  # Add border to headings
            relief="solid",
        )
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

        # Create a treeview for the table
        columns = ("No", "Item ID", "Status", "Result")
        self.tree = ttkb.Treeview(self, columns=columns, show="headings")
        self.tree.heading("No", text="No")
        self.tree.heading("Item ID", text="Item ID")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Result", text="Result")

        # Configure column widths
        self.tree.column("No", width=40, stretch=False, anchor=tkinter.CENTER)        # Set width for "No" column
        self.tree.column("Item ID", width=120, stretch=False, anchor=tkinter.CENTER)  # Set width for "Item ID" column
        self.tree.column("Status", width=200, anchor=tkinter.CENTER)   # Set width for "Status" column
        self.tree.column("Result", width=120, stretch=False, anchor=tkinter.CENTER)   # Set width for "Result" column
        
        self.treeScroll = ttkb.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.treeScroll.set)

        # Add the treeview to the window
        self.tree.grid(row=1, column=0, columnspan=6, padx=10, pady=10, sticky="nsew")
        self.treeScroll.grid(row=1, column=6, sticky='nse')

        self.treeScroll.configure(command=self.tree.yview)
        
        # Bind right-click to show context menu
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # Add a text field to show the status
        self.status_label = ttkb.Label(self, name="status_label", text="Status: Ready")
        self.status_label.grid(row=2, column=0, columnspan=6, padx=10, pady=10, sticky="ew")
        
        # Configure grid weights to allow resizing
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.ebay = EBaySDK(self)
        self.ebay.get_token()

    def retry_failed_items(self):
        pass
        # Open a dialog with one input field and an OK button
        # user_input = simpledialog.askstring("Input", "Please enter your text:")
        # if user_input:
        #     # Add the input text to the table
        #     self.tree.insert("", "end", values=(len(self.tree.get_children()) + 1, user_input, "Input", "Success"))

    def update_status_in_table_row(self, row, text):
        # Get all item IDs
        item_ids = self.tree.get_children()
        
        # Ensure the row index is within bounds
        if 0 <= row < len(item_ids):
            item_id = item_ids[row]
            # Update the status for the correct item
            self.tree.set(item_id, "Status", text)
        else:
            print(f"Row {row} is out of bounds.")

    def update_cell_in_table(self, row, column, text):
        # Get all item IDs
        item_ids = self.tree.get_children()

        # Ensure the row index is within bounds
        if 0 <= row < len(item_ids):
            item_id = item_ids[row]
            # Update the status for the correct item
            self.tree.set(item_id, column, text)
        else:
            print(f"Row {row} is out of bounds.")

    def addFixedItem(self, item: dict, row: int, scheduleAfter: int):

        addFixedPriceItemXML = ET.Element('AddFixedPriceItemRequest')
        addFixedPriceItemXML.set('xmlns', 'urn:ebay:apis:eBLBaseComponents')

        itemXML = ET.SubElement(addFixedPriceItemXML, 'Item')

        title = ET.SubElement(itemXML, 'Title')
        title.text = item['title']

        description = ET.SubElement(itemXML, 'Description')
        description.text = item['description']

        startPrice = ET.SubElement(itemXML, 'StartPrice')
        startPrice.text = item['price']['value']

        currency = ET.SubElement(itemXML, 'Currency')
        currency.text = item['price']['currency']
        
        primaryCategory = ET.SubElement(itemXML, 'PrimaryCategory')
        categoryID = ET.SubElement(primaryCategory, 'CategoryID')
        categoryID.text = item['categoryId']

        dispatchTimeMax = ET.SubElement(itemXML, 'DispatchTimeMax')
        dispatchTimeMax.text = "3"

        scheduleTime = ET.SubElement(itemXML, "ScheduleTime")
        scheduleTime.text = (datetime.now(UTC) + timedelta(minutes=scheduleAfter)).isoformat()

        pictureDetails = ET.SubElement(itemXML, 'PictureDetails')
        galleryType = ET.SubElement(pictureDetails, 'GalleryType')
        galleryType.text = "Gallery"

        pictureSource = ET.SubElement(pictureDetails, 'PictureSource')
        pictureSource.text = "EPS"
        
        self.update_status_in_table_row(row, "Uploading Main Picture...")
        result = self.ebay.upload_site_hosted_picture(item['image']['imageUrl'])
        if result == None :
            self.update_status_in_table_row(row, "Failed to upload main picture")
        else :
            self.update_status_in_table_row(row, "Uploaded Main Picture")
            pictureURL = ET.SubElement(pictureDetails, 'PictureURL')
            pictureURL.text = result

        # self.update_status_in_table_row(row, f"Detected {len(item['additionalImages'])} additional pictures")
        # for picture in item['additionalImages']:
        #     self.update_status_in_table_row(row, f"Uploading {picture['imageUrl']}")
        #     pictureURL = ET.SubElement(pictureDetails, 'PictureURL')
        #     result = self.ebay.upload_site_hosted_picture(picture['imageUrl'])
        #     if result == None :
        #         self.update_status_in_table_row(row, f"Failed to upload additional picture {picture['imageUrl']}")
        #     else :
        #         self.update_status_in_table_row(row, f"Uploaded Additional Picture {picture['imageUrl']}")
        #     pictureURL.text = result

        conditionID = ET.SubElement(itemXML, 'ConditionID')
        conditionID.text = item['conditionId']

        country = ET.SubElement(itemXML, 'Country')
        country.text = "US"

        location = ET.SubElement(itemXML, 'Location')
        location.text = "Manassas, VA 20110, USA"

        postalCode = ET.SubElement(itemXML, 'PostalCode')
        postalCode.text = '20110'

        itemSpecifics = ET.SubElement(itemXML, 'ItemSpecifics')
        for aspect in item['localizedAspects']:
            nameValueList = ET.SubElement(itemSpecifics, 'NameValueList')
            name = ET.SubElement(nameValueList, 'Name')
            name.text = aspect['name']
            value = ET.SubElement(nameValueList, 'Value')
            value.text = aspect['value']

        listingType = ET.SubElement(itemXML, 'ListingType')
        listingType.text = "FixedPriceItem"

        listingDuration = ET.SubElement(itemXML, 'ListingDuration')
        listingDuration.text = "GTC"

        quantity = ET.SubElement(itemXML, 'Quantity')
        quantity.text = "1"

        shippingDetails = ET.SubElement(itemXML, 'ShippingDetails')
        shippingType = ET.SubElement(shippingDetails, 'ShippingType')
        shippingType.text = "Flat"
        shippingServiceOptions = ET.SubElement(shippingDetails, 'ShippingServiceOptions')
        shippingServiceCost = ET.SubElement(shippingServiceOptions, 'ShippingServiceCost')
        shippingServiceCost.text = "0.00"
        shippingServicePriority = ET.SubElement(shippingServiceOptions, 'ShippingServicePriority')
        shippingServicePriority.text = "1"
        shippingService = ET.SubElement(shippingServiceOptions, 'ShippingService')
        shippingService.text = "USPSMedia"

        shippingLocations = item['shipToLocations']['regionIncluded']
        for location in shippingLocations:
            shippingLocation = ET.SubElement(itemXML, 'ShipToLocations')
            shippingLocation.text = location['regionId']

        excludeShippingLocations = item['shipToLocations']['regionExcluded']
        for location in excludeShippingLocations:
            excludeshippingLocationXML = ET.SubElement(shippingDetails, 'ExcludeShipToLocation')
            excludeshippingLocationXML.text = location['regionId']

        # Convert the ElementTree to a string with XML declaration
        xml_string = ET.tostring(addFixedPriceItemXML, encoding='utf-8', xml_declaration=True)

        response = self.ebay.execute_with_xml('AddFixedPriceItem', xml_string.decode('utf-8'))
        
        if 'ErrorCode' in response :
            self.update_status_in_table_row(row, f"Error: {response['ErrorCode']}")
            # self.update_status_in_table_row(row, "Detected the same listing in your store. Revising the listing...")
            # if(response['ErrorCode'] == '21918013') :
            #     response = self.ebay.execute_with_xml('ReviseFixedPriceItem', xml_string.decode('utf-8'))
            #     self.update_status_in_table_row(row, "Revised the listing")
        else :
            self.update_status_in_table_row(row, "Added the listing")
            self.update_cell_in_table(row, 3, response)
    
    
    def addFixedItemWithVariants(self,item: dict, row: int, scheduleAfter: int):
        commonItem = item['items'][0]
        
        addFixedPriceItemXML = ET.Element('AddFixedPriceItemRequest')
        addFixedPriceItemXML.set('xmlns', 'urn:ebay:apis:eBLBaseComponents')

        itemXML = ET.SubElement(addFixedPriceItemXML, 'Item')

        title = ET.SubElement(itemXML, 'Title')
        title.text = commonItem['title']

        description = ET.SubElement(itemXML, 'Description')
        description.text = commonItem['shortDescription']

        currency = ET.SubElement(itemXML, 'Currency')
        currency.text = commonItem['price']['currency']
        
        primaryCategory = ET.SubElement(itemXML, 'PrimaryCategory')
        categoryID = ET.SubElement(primaryCategory, 'CategoryID')
        categoryID.text = commonItem['categoryId']

        dispatchTimeMax = ET.SubElement(itemXML, 'DispatchTimeMax')
        dispatchTimeMax.text = "3"

        scheduleTime = ET.SubElement(itemXML, "ScheduleTime")
        scheduleTime.text = (datetime.now(UTC) + timedelta(minutes=scheduleAfter)).isoformat()

        pictureDetails = ET.SubElement(itemXML, 'PictureDetails')
        galleryType = ET.SubElement(pictureDetails, 'GalleryType')
        galleryType.text = "Gallery"

        pictureSource = ET.SubElement(pictureDetails, 'PictureSource')
        pictureSource.text = "EPS"

        conditionID = ET.SubElement(itemXML, 'ConditionID')
        conditionID.text = commonItem['conditionId']

        country = ET.SubElement(itemXML, 'Country')
        country.text = "US"

        location = ET.SubElement(itemXML, 'Location')
        location.text = "Manassas, VA 20110, USA"

        postalCode = ET.SubElement(itemXML, 'PostalCode')
        postalCode.text = '20110'

        listingType = ET.SubElement(itemXML, 'ListingType')
        listingType.text = "FixedPriceItem"

        listingDuration = ET.SubElement(itemXML, 'ListingDuration')
        listingDuration.text = "GTC"

        shippingDetails = ET.SubElement(itemXML, 'ShippingDetails')
        shippingType = ET.SubElement(shippingDetails, 'ShippingType')
        shippingType.text = "Flat"
        shippingServiceOptions = ET.SubElement(shippingDetails, 'ShippingServiceOptions')
        shippingServiceCost = ET.SubElement(shippingServiceOptions, 'ShippingServiceCost')
        shippingServiceCost.text = "0.00"
        shippingServicePriority = ET.SubElement(shippingServiceOptions, 'ShippingServicePriority')
        shippingServicePriority.text = "1"
        shippingService = ET.SubElement(shippingServiceOptions, 'ShippingService')
        shippingService.text = "USPSMedia"

        # shippingLocations = commonItem['shipToLocations']['regionIncluded']
        # for location in shippingLocations:
        shippingLocation = ET.SubElement(itemXML, 'ShipToLocations')
        shippingLocation.text = "US"

        # excludeShippingLocations = commonItem['shipToLocations']['regionExcluded']
        # for location in excludeShippingLocations:
        #     excludeshippingLocationXML = ET.SubElement(shippingDetails, 'ExcludeShipToLocation')
        #     excludeshippingLocationXML.text = location['regionId']

        from collections import defaultdict

        aspectsData = defaultdict(set)
        variations = ET.SubElement(itemXML, 'Variations')

        for variant in item['items']:
            for aspect in variant['localizedAspects']:
                aspectsData[aspect['name']].add(aspect['value'])

        # aspectsData = {name: values for name, values in aspectsData.items() if len(values) > 1}

        # variationPictures = ET.SubElement(variations, 'Pictures')

        picturesSet = {}
        for variant in item['items']:
            variation = ET.SubElement(variations, 'Variation')
            imageUrl = variant['image']['imageUrl']

            variationQuantity = ET.SubElement(variation, 'Quantity')
            variationQuantity.text = '1'
            variationStartPrice = ET.SubElement(variation, 'StartPrice')
            variationStartPrice.text = variant['price']['value']
            variationSpecifics = ET.SubElement(variation, 'VariationSpecifics')
            variationSpecifisItem = variant['localizedAspects']
            for aspect in variationSpecifisItem:
                if aspect['name'].lower() not in variant:
                    continue
                
                if len(aspectsData[aspect['name']]) < 2 :
                    continue
                
                if imageUrl not in picturesSet :
                    picturesSet[imageUrl] = {}
                    picturesSet[imageUrl][aspect['name']] = set([aspect['value']])
                else :
                    if aspect['name'] not in picturesSet[imageUrl] :
                        picturesSet[imageUrl][aspect['name']] = set([aspect['value']])
                    else :
                        picturesSet[imageUrl][aspect['name']].add(aspect['value'])

                nameValueList = ET.SubElement(variationSpecifics, 'NameValueList')
                name = ET.SubElement(nameValueList, 'Name')
                name.text = aspect['name']
                value = ET.SubElement(nameValueList, 'Value')
                value.text = aspect['value']

        variationSpecificsSet = ET.SubElement(variations, 'VariationSpecificsSet')
        for aspect in aspectsData:
            if len(aspectsData[aspect]) < 2 :
                continue
            nameValueList = ET.SubElement(variationSpecificsSet, 'NameValueList')
            name = ET.SubElement(nameValueList, 'Name')
            name.text = aspect
            for aspectValue in aspectsData[aspect]:
                value = ET.SubElement(nameValueList, 'Value')
                value.text = aspectValue

        itemSpecifics = ET.SubElement(itemXML, 'ItemSpecifics')
        for aspect in commonItem['localizedAspects']:
            if len(aspectsData[aspect['name']]) > 1 :
                continue
            nameValueList = ET.SubElement(itemSpecifics, 'NameValueList')
            name = ET.SubElement(nameValueList, 'Name')
            name.text = aspect['name']
            value = ET.SubElement(nameValueList, 'Value')
            value.text = aspect['value']

        refinedPictures = {}
        for imageUrl in picturesSet :
            variantSets = picturesSet[imageUrl]
            for variantName in variantSets :
                if len(variantSets[variantName]) > 1 :
                    continue
                variantValue = variantSets[variantName]
                if variantName not in refinedPictures :
                    refinedPictures[variantName] = {}
                    refinedPictures[variantName][list(variantValue)[0]] = imageUrl
                else :
                    refinedPictures[variantName][list(variantValue)[0]] = imageUrl

        pictures = ET.SubElement(variations, 'Pictures')
        # Insert Picture Data
        for variantName in refinedPictures :
            variantSpecificName = ET.SubElement(pictures, 'VariationSpecificName')
            variantSpecificName.text = variantName

            variantSets = refinedPictures[variantName]
            for variantValue in variantSets :
                imageUrl = variantSets[variantValue]
                self.update_status_in_table_row(row, f"Uploading Picture for {variantName} : {variantValue}")
                result = self.ebay.upload_site_hosted_picture(imageUrl)
                if result == None :
                    self.update_status_in_table_row(row, f"Failed to upload picture for {variantName} : {variantValue}")
                else :
                    self.update_status_in_table_row(row, f"Uploaded Picture for {variantName} : {variantValue}")
                    variantSpecificPictureSet = ET.SubElement(pictures, 'VariationSpecificPictureSet')
                    variantSpecificValue = ET.SubElement(variantSpecificPictureSet, 'VariationSpecificValue')
                    variantSpecificValue.text = variantValue
                    variantSpecificPictureURL = ET.SubElement(variantSpecificPictureSet, 'PictureURL')
                    variantSpecificPictureURL.text = result

            # pictureURL = ET.SubElement(pictureDetails, 'PictureURL')
            # pictureURL.text = imageUrl
            pass
        # Convert the ElementTree to a string with XML declaration
        xml_string = ET.tostring(addFixedPriceItemXML, encoding='utf-8', xml_declaration=True)
        
        # with open('output.xml', 'wb') as file:
        #     file.write(xml_string)
        # return

        response = self.ebay.execute_with_xml('AddFixedPriceItem', xml_string.decode('utf-8'))
        
        if 'ErrorCode' in response :
            self.update_status_in_table_row(row, f"Error: {response['ErrorCode']}")
            # print("Detected the same listing in your store. Revising the listing...")
            # if(response['ErrorCode'] == '21918013') :
            #     response = ebay.execute_with_xml('ReviseFixedPriceItem', xml_string.decode('utf-8'))
            #     print(response)
        else :
            self.update_status_in_table_row(row, "Added the listing")
            self.update_cell_in_table(row, 3, response)
            # print(response)

    @threaded
    def run_duplicate_item(self, item_id, index, scheduleAfter):
        # Get the json data from the ebay with item id
        # self.ebay.execute('EndItem', {
        #     'ItemID': "110567061411",
        #     'EndingReason': 'NotAvailable'
        # })
        # return
        
        # Duplicate the item with json data
        try :
            response = self.ebay.get_item_by_legacy_id(item_id)
            if 'errors' in response :
                error = response['errors'][0]
                if error['errorId'] == 1001 :
                    self.status_label.config(text="Invalid access token. Please authorize first to continue duplication...")
                    self.duplicate_button.config(state="disabled")
                    self.update_status_in_table_row(index, f"Invalid access token. Try again later...")
                    return
                
                response = self.ebay.get_items_by_item_group(item_id)
                if 'errors' in response:
                    error = response['errors'][0]
                    if error['errorId'] == 1001 :
                        self.duplicate_button.config(state="disabled")
                        self.status_label.config(text="Invalid access token. Please authorize first to continue duplication...")
                        self.update_status_in_table_row(index, f"Invalid access token. Try again later...")
                    else:
                        self.update_status_in_table_row(index, f"Failed to duplicate item: Can't get item from ebay. Please check the item id...")
                    return
                else:
                    self.addFixedItemWithVariants(response, index, scheduleAfter)
            else :
                itemDetail = response
                self.addFixedItem(itemDetail, index, scheduleAfter)
        except Exception as e:
            self.update_status_in_table_row(index, f"Failed to duplicate item: {e}")

    def duplicate_text(self):
        text = self.entry.get()
        scheduleAfter = self.entrySchedule.get()
        if not scheduleAfter:
            scheduleAfter = 0
        if text:
            # Add the duplicated text to the table
            self.tree.insert("", "end", values=(len(self.tree.get_children()) + 1, text, "Processing", ""))
            self.run_duplicate_item(text, len(self.tree.get_children()) - 1, int(scheduleAfter))

    def authorize(self):
        self.ebay.get_token(isForce=True)

    def validate_number(self, P):
        # Allow only empty string or string with digits
        return P.isdigit() or P == ""

    def show_context_menu(self, event):
        # Create a context menu
        menu = ttkb.Menu(self, tearoff=0)
        menu.add_command(label="Copy", command=self.copy_selected_item)
        
        # Display the menu
        menu.post(event.x_root, event.y_root)

    def copy_selected_item(self):
        # Get selected item
        selected_item = self.tree.selection()
        if selected_item:
            # Get the values of the selected item
            item_values = self.tree.item(selected_item, "values")
            # Copy the first column value to the clipboard
            self.clipboard_clear()
            self.clipboard_append(item_values[3])
            print(f"Copied to clipboard: {item_values[3]}")

def main():
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()
