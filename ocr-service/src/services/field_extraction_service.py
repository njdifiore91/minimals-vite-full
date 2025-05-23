# ocr-service/src/services/field_extraction_service.py

import logging
from typing import Dict, List, Optional, Tuple, Any, Union
import json
import re

import tensorflow as tf
import numpy as np

from ..types.extraction import (
    ExtractedField, 
    ConfidenceScore, 
    ExtractedData, 
    FieldLocation, 
    ExtractionMetadata,
    JSONSchema
)
from ..types.models import OCRModelType, ModelResult
from ..types.errors import ServiceError, ErrorCategory, Result
from ..types.config import ConfigDict

from ..utils.logging_utils import log_with_context
from ..utils.text_utils import clean_text, normalize_field_value
from ..utils.error_utils import create_error
from ..utils.validation_utils import validate_field_value

from ..models.structure_recognition_model import StructureRecognitionModel

logger = logging.getLogger(__name__)

class FieldExtractionService:
    """
    Service for extracting structured data from OCR results.
    
    This service is responsible for:
    1. Identifying document structure (forms, tables, sections)
    2. Extracting key-value pairs from OCR text
    3. Normalizing and standardizing field values
    4. Applying document type-specific extraction rules
    5. Formatting extracted data as JSON
    6. Validating and correcting extracted fields
    
    The service transforms raw OCR text into structured JSON data for downstream processing.
    """
    
    def __init__(self, config: ConfigDict):
        """
        Initialize the FieldExtractionService with configuration.
        
        Args:
            config: Configuration dictionary containing extraction settings
        """
        self.config = config
        self.structure_model = StructureRecognitionModel(config)
        
        # Load document type-specific extraction templates
        self.extraction_templates = self._load_extraction_templates()
        
        # Field normalization rules
        self.normalization_rules = self._load_normalization_rules()
        
        # Field validation rules
        self.validation_rules = self._load_validation_rules()
        
        # Regular expressions for common field patterns
        self.field_patterns = self._load_field_patterns()
        
        log_with_context(logger.info, "FieldExtractionService initialized")
    
    def extract_structured_data(self, ocr_result: ModelResult, document_type: str) -> Result[ExtractedData]:
        """
        Extract structured data from OCR results based on document type.
        
        Args:
            ocr_result: The raw OCR result containing extracted text and metadata
            document_type: The type of document (e.g., 'loan_application', 'tax_return')
            
        Returns:
            Result containing ExtractedData with structured fields or an error
        """
        try:
            log_with_context(logger.info, f"Extracting structured data for document type: {document_type}")
            
            # Recognize document structure (forms, tables, sections)
            structure_result = self.recognize_structure(ocr_result, document_type)
            if isinstance(structure_result, ServiceError):
                return structure_result
            
            document_structure = structure_result
            
            # Extract fields based on document structure and type
            extraction_result = self._extract_fields_by_document_type(
                ocr_result, 
                document_structure, 
                document_type
            )
            if isinstance(extraction_result, ServiceError):
                return extraction_result
                
            extracted_fields = extraction_result
            
            # Normalize and standardize field values
            normalized_fields = self._normalize_fields(extracted_fields, document_type)
            
            # Validate extracted fields
            validated_fields = self._validate_fields(normalized_fields, document_type)
            
            # Format as JSON with proper schema
            formatted_data = self._format_as_json(validated_fields, document_type)
            
            log_with_context(
                logger.info, 
                f"Successfully extracted {len(validated_fields)} fields from {document_type}"
            )
            
            return formatted_data
        except Exception as e:
            error = create_error(
                ErrorCategory.PROCESSING_ERROR,
                f"Failed to extract structured data: {str(e)}",
                exception=e
            )
            log_with_context(logger.error, error.message, error=error)
            return error
    
    def recognize_structure(self, ocr_result: ModelResult, document_type: str) -> Result[Dict[str, Any]]:
        """
        Recognize the structure of a document including forms, tables, and sections.
        
        Args:
            ocr_result: The raw OCR result containing extracted text and metadata
            document_type: The type of document
            
        Returns:
            Result containing document structure information or an error
        """
        try:
            log_with_context(logger.info, f"Recognizing structure for document type: {document_type}")
            
            # Use the structure recognition model to identify document components
            structure = self.structure_model.recognize(ocr_result.text, document_type)
            
            # Extract forms from the document
            forms = self._identify_forms(structure, ocr_result.text)
            
            # Extract tables from the document
            tables = self._identify_tables(structure, ocr_result.text)
            
            # Extract sections from the document
            sections = self._identify_sections(structure, ocr_result.text)
            
            document_structure = {
                "forms": forms,
                "tables": tables,
                "sections": sections,
                "page_count": ocr_result.metadata.get("page_count", 1),
                "orientation": ocr_result.metadata.get("orientation", "portrait"),
                "language": ocr_result.metadata.get("language", "en")
            }
            
            log_with_context(
                logger.info, 
                f"Structure recognition complete: {len(forms)} forms, {len(tables)} tables, {len(sections)} sections"
            )
            
            return document_structure
        except Exception as e:
            error = create_error(
                ErrorCategory.PROCESSING_ERROR,
                f"Failed to recognize document structure: {str(e)}",
                exception=e
            )
            log_with_context(logger.error, error.message, error=error)
            return error
    
    def extract_key_value_pairs(self, text: str, document_type: str) -> List[Tuple[str, str, ConfidenceScore]]:
        """
        Extract key-value pairs from OCR text.
        
        Args:
            text: The OCR text to extract key-value pairs from
            document_type: The type of document
            
        Returns:
            List of tuples containing (key, value, confidence_score)
        """
        log_with_context(logger.info, f"Extracting key-value pairs for document type: {document_type}")
        
        key_value_pairs = []
        
        # Get document-specific patterns for key-value extraction
        patterns = self.field_patterns.get(document_type, self.field_patterns.get("default", {}))
        
        # Apply general key-value extraction for labeled fields
        # Pattern: Key: Value or Key - Value
        general_kv_pattern = r"([\w\s\-&]+)[:|-]\s*([\w\s\-\.,;\$%#@!\(\)\/'"]+)"
        matches = re.finditer(general_kv_pattern, text)
        
        for match in matches:
            key = match.group(1).strip()
            value = match.group(2).strip()
            
            # Skip if key or value is too short
            if len(key) < 2 or len(value) < 1:
                continue
                
            # Calculate confidence based on pattern match quality
            confidence = self._calculate_key_value_confidence(key, value, document_type)
            
            key_value_pairs.append((key, value, confidence))
        
        # Apply document-specific patterns for known fields
        for field_name, pattern in patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                if match.lastindex and match.lastindex >= 1:
                    value = match.group(1).strip()
                    # Calculate confidence based on pattern match quality
                    confidence = self._calculate_pattern_match_confidence(match, pattern)
                    key_value_pairs.append((field_name, value, confidence))
        
        log_with_context(logger.info, f"Extracted {len(key_value_pairs)} key-value pairs")
        return key_value_pairs
    
    def extract_table_data(self, table_structure: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """
        Extract structured data from tables identified in the document.
        
        Args:
            table_structure: The structure information for the table
            text: The OCR text containing the table
            
        Returns:
            List of dictionaries representing table rows with column values
        """
        log_with_context(logger.info, "Extracting data from table structure")
        
        table_data = []
        
        # Extract table boundaries
        table_text = text[table_structure["start_idx"]:table_structure["end_idx"]]
        
        # Extract header row to identify columns
        headers = table_structure.get("headers", [])
        if not headers and "header_row" in table_structure:
            header_text = table_text[table_structure["header_row"]["start_idx"]:table_structure["header_row"]["end_idx"]]
            headers = self._extract_table_headers(header_text)
        
        # Extract data rows
        rows = table_structure.get("rows", [])
        for row in rows:
            row_text = table_text[row["start_idx"]:row["end_idx"]]
            row_data = self._extract_row_data(row_text, headers, table_structure)
            if row_data:
                table_data.append(row_data)
        
        log_with_context(logger.info, f"Extracted {len(table_data)} rows from table")
        return table_data
    
    def _extract_fields_by_document_type(self, 
                                        ocr_result: ModelResult, 
                                        document_structure: Dict[str, Any], 
                                        document_type: str) -> Result[List[ExtractedField]]:
        """
        Extract fields based on document type and structure.
        
        Args:
            ocr_result: The raw OCR result
            document_structure: The recognized document structure
            document_type: The type of document
            
        Returns:
            Result containing list of extracted fields or an error
        """
        try:
            extracted_fields = []
            
            # Get document template if available
            template = self.extraction_templates.get(document_type)
            
            # Extract key-value pairs from the entire document
            key_value_pairs = self.extract_key_value_pairs(ocr_result.text, document_type)
            
            # Convert key-value pairs to ExtractedField objects
            for key, value, confidence in key_value_pairs:
                # Map to standardized field name if template is available
                field_name = key
                if template and key in template.get("field_mapping", {}):
                    field_name = template["field_mapping"][key]
                
                # Create field location (approximate based on text search)
                location = self._find_field_location(key, value, ocr_result.text)
                
                extracted_fields.append(ExtractedField(
                    name=field_name,
                    value=value,
                    confidence=confidence,
                    location=location,
                    metadata={
                        "source": "key_value_extraction",
                        "original_name": key if field_name != key else None
                    }
                ))
            
            # Extract fields from forms
            for form in document_structure.get("forms", []):
                form_fields = self._extract_form_fields(form, ocr_result.text, document_type)
                extracted_fields.extend(form_fields)
            
            # Extract fields from tables
            for table in document_structure.get("tables", []):
                table_data = self.extract_table_data(table, ocr_result.text)
                # Store table data as a special field
                if table_data:
                    table_name = table.get("name", f"table_{len(extracted_fields)}")
                    extracted_fields.append(ExtractedField(
                        name=table_name,
                        value=json.dumps(table_data),  # Store as JSON string
                        confidence=ConfidenceScore(0.9),  # Tables typically have high confidence
                        location=FieldLocation(
                            page=table.get("page", 0),
                            x=table.get("x", 0),
                            y=table.get("y", 0),
                            width=table.get("width", 0),
                            height=table.get("height", 0)
                        ),
                        metadata={
                            "source": "table_extraction",
                            "row_count": len(table_data),
                            "is_table": True
                        }
                    ))
            
            # Apply document-specific extraction logic
            if document_type == "loan_application":
                loan_fields = self._extract_loan_application_fields(ocr_result.text, document_structure)
                extracted_fields.extend(loan_fields)
            elif document_type == "tax_return":
                tax_fields = self._extract_tax_return_fields(ocr_result.text, document_structure)
                extracted_fields.extend(tax_fields)
            elif document_type == "bank_statement":
                bank_fields = self._extract_bank_statement_fields(ocr_result.text, document_structure)
                extracted_fields.extend(bank_fields)
            elif document_type == "identity_document":
                id_fields = self._extract_identity_document_fields(ocr_result.text, document_structure)
                extracted_fields.extend(id_fields)
            
            # Remove duplicate fields (prefer higher confidence)
            deduplicated_fields = self._deduplicate_fields(extracted_fields)
            
            log_with_context(
                logger.info, 
                f"Extracted {len(deduplicated_fields)} fields for document type {document_type}"
            )
            
            return deduplicated_fields
        except Exception as e:
            error = create_error(
                ErrorCategory.PROCESSING_ERROR,
                f"Failed to extract fields for document type {document_type}: {str(e)}",
                exception=e
            )
            log_with_context(logger.error, error.message, error=error)
            return error
    
    def _normalize_fields(self, fields: List[ExtractedField], document_type: str) -> List[ExtractedField]:
        """
        Normalize and standardize field values based on field type and document type.
        
        Args:
            fields: List of extracted fields
            document_type: The type of document
            
        Returns:
            List of normalized fields
        """
        log_with_context(logger.info, f"Normalizing {len(fields)} fields for document type {document_type}")
        
        normalized_fields = []
        
        # Get normalization rules for this document type
        type_rules = self.normalization_rules.get(document_type, {})
        default_rules = self.normalization_rules.get("default", {})
        
        for field in fields:
            # Skip table fields (already in structured format)
            if field.metadata.get("is_table", False):
                normalized_fields.append(field)
                continue
                
            # Get field-specific normalization rule
            rule = type_rules.get(field.name, default_rules.get(field.name))
            
            if rule:
                field_type = rule.get("type", "string")
                format_spec = rule.get("format")
                
                # Apply normalization based on field type
                normalized_value = normalize_field_value(field.value, field_type, format_spec)
                
                # Create new field with normalized value
                normalized_field = ExtractedField(
                    name=field.name,
                    value=normalized_value,
                    confidence=field.confidence,
                    location=field.location,
                    metadata={
                        **field.metadata,
                        "original_value": field.value if normalized_value != field.value else None,
                        "normalized": True,
                        "field_type": field_type
                    }
                )
                normalized_fields.append(normalized_field)
            else:
                # No specific rule, just clean the text
                cleaned_value = clean_text(field.value)
                if cleaned_value != field.value:
                    field.metadata["original_value"] = field.value
                    field.value = cleaned_value
                    field.metadata["normalized"] = True
                normalized_fields.append(field)
        
        log_with_context(logger.info, f"Normalized {len(normalized_fields)} fields")
        return normalized_fields
    
    def _validate_fields(self, fields: List[ExtractedField], document_type: str) -> List[ExtractedField]:
        """
        Validate extracted fields and attempt to correct errors.
        
        Args:
            fields: List of normalized fields
            document_type: The type of document
            
        Returns:
            List of validated fields
        """
        log_with_context(logger.info, f"Validating {len(fields)} fields for document type {document_type}")
        
        validated_fields = []
        
        # Get validation rules for this document type
        type_rules = self.validation_rules.get(document_type, {})
        default_rules = self.validation_rules.get("default", {})
        
        for field in fields:
            # Skip table fields (handled separately)
            if field.metadata.get("is_table", False):
                validated_fields.append(field)
                continue
                
            # Get field-specific validation rule
            rule = type_rules.get(field.name, default_rules.get(field.name))
            
            if rule:
                field_type = field.metadata.get("field_type", rule.get("type", "string"))
                constraints = rule.get("constraints", {})
                
                # Validate field value
                is_valid, corrected_value, validation_message = validate_field_value(
                    field.value, field_type, constraints
                )
                
                if is_valid:
                    # Field is valid, no changes needed
                    if validation_message:
                        field.metadata["validation_message"] = validation_message
                    validated_fields.append(field)
                elif corrected_value is not None:
                    # Field was corrected
                    corrected_field = ExtractedField(
                        name=field.name,
                        value=corrected_value,
                        confidence=field.confidence * 0.9,  # Reduce confidence slightly for corrected fields
                        location=field.location,
                        metadata={
                            **field.metadata,
                            "original_value": field.metadata.get("original_value", field.value),
                            "corrected": True,
                            "validation_message": validation_message
                        }
                    )
                    validated_fields.append(corrected_field)
                else:
                    # Field is invalid and couldn't be corrected
                    # Mark as low confidence
                    invalid_field = ExtractedField(
                        name=field.name,
                        value=field.value,
                        confidence=ConfidenceScore(min(field.confidence.value, 0.5)),  # Cap confidence at 0.5
                        location=field.location,
                        metadata={
                            **field.metadata,
                            "validation_failed": True,
                            "validation_message": validation_message
                        }
                    )
                    validated_fields.append(invalid_field)
            else:
                # No validation rule, keep as is
                validated_fields.append(field)
        
        log_with_context(logger.info, f"Validated {len(validated_fields)} fields")
        return validated_fields
    
    def _format_as_json(self, fields: List[ExtractedField], document_type: str) -> ExtractedData:
        """
        Format extracted fields as JSON according to document type schema.
        
        Args:
            fields: List of validated fields
            document_type: The type of document
            
        Returns:
            ExtractedData object with formatted JSON
        """
        log_with_context(logger.info, f"Formatting {len(fields)} fields as JSON for document type {document_type}")
        
        # Create a dictionary to hold the structured data
        data = {}
        tables = {}
        metadata = {}
        
        # Process regular fields
        for field in fields:
            if field.metadata.get("is_table", False):
                # Handle table data separately
                tables[field.name] = json.loads(field.value)
            else:
                # Add field to appropriate section based on metadata
                section = field.metadata.get("section", "main")
                
                if section not in data:
                    data[section] = {}
                    
                data[section][field.name] = {
                    "value": field.value,
                    "confidence": field.confidence.value
                }
                
                # Add metadata if present
                if field.metadata:
                    filtered_metadata = {k: v for k, v in field.metadata.items() 
                                       if k not in ["section", "is_table", "source"] and v is not None}
                    if filtered_metadata:
                        data[section][field.name]["metadata"] = filtered_metadata
        
        # Add tables to the data structure if present
        if tables:
            data["tables"] = tables
            
        # Create extraction metadata
        extraction_metadata = ExtractionMetadata(
            document_type=document_type,
            field_count=len(fields),
            table_count=len(tables),
            average_confidence=self._calculate_average_confidence(fields),
            timestamp=self._get_current_timestamp()
        )
        
        # Create JSON schema based on document type
        schema = self._create_json_schema(document_type, fields)
        
        # Create the final ExtractedData object
        extracted_data = ExtractedData(
            data=data,
            metadata=extraction_metadata,
            schema=schema
        )
        
        log_with_context(logger.info, f"Formatted data as JSON with {len(data)} sections")
        return extracted_data
    
    def _identify_forms(self, structure: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """
        Identify forms within the document structure.
        
        Args:
            structure: The document structure from the recognition model
            text: The OCR text
            
        Returns:
            List of form structures with field information
        """
        forms = []
        
        # Extract form regions from structure
        for form_region in structure.get("form_regions", []):
            form_text = text[form_region["start_idx"]:form_region["end_idx"]]
            
            # Identify form fields within the form
            fields = []
            for field in form_region.get("fields", []):
                field_text = form_text[field["start_idx"]:field["end_idx"]]
                
                # Extract label and value
                label_text = field_text[:field.get("label_end_idx", 0)].strip()
                value_text = field_text[field.get("label_end_idx", 0):].strip()
                
                fields.append({
                    "label": label_text,
                    "value": value_text,
                    "x": field.get("x", 0),
                    "y": field.get("y", 0),
                    "width": field.get("width", 0),
                    "height": field.get("height", 0),
                    "page": field.get("page", 0)
                })
            
            forms.append({
                "name": form_region.get("name", "unnamed_form"),
                "fields": fields,
                "x": form_region.get("x", 0),
                "y": form_region.get("y", 0),
                "width": form_region.get("width", 0),
                "height": form_region.get("height", 0),
                "page": form_region.get("page", 0),
                "start_idx": form_region["start_idx"],
                "end_idx": form_region["end_idx"]
            })
        
        return forms
    
    def _identify_tables(self, structure: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """
        Identify tables within the document structure.
        
        Args:
            structure: The document structure from the recognition model
            text: The OCR text
            
        Returns:
            List of table structures with row and column information
        """
        tables = []
        
        # Extract table regions from structure
        for table_region in structure.get("table_regions", []):
            table_text = text[table_region["start_idx"]:table_region["end_idx"]]
            
            # Extract header row
            header_row = table_region.get("header_row", {})
            headers = []
            
            if header_row:
                header_text = table_text[header_row.get("start_idx", 0):header_row.get("end_idx", 0)]
                headers = self._extract_table_headers(header_text)
            
            # Extract data rows
            rows = []
            for row in table_region.get("rows", []):
                row_text = table_text[row.get("start_idx", 0):row.get("end_idx", 0)]
                
                # Extract cells if available
                cells = []
                for cell in row.get("cells", []):
                    cell_text = row_text[cell.get("start_idx", 0):cell.get("end_idx", 0)]
                    cells.append({
                        "text": cell_text.strip(),
                        "column_index": cell.get("column_index", 0),
                        "x": cell.get("x", 0),
                        "y": cell.get("y", 0),
                        "width": cell.get("width", 0),
                        "height": cell.get("height", 0)
                    })
                
                rows.append({
                    "text": row_text.strip(),
                    "cells": cells,
                    "start_idx": row.get("start_idx", 0),
                    "end_idx": row.get("end_idx", 0),
                    "x": row.get("x", 0),
                    "y": row.get("y", 0),
                    "width": row.get("width", 0),
                    "height": row.get("height", 0)
                })
            
            tables.append({
                "name": table_region.get("name", "unnamed_table"),
                "headers": headers,
                "rows": rows,
                "column_count": table_region.get("column_count", len(headers)),
                "row_count": len(rows),
                "header_row": header_row,
                "x": table_region.get("x", 0),
                "y": table_region.get("y", 0),
                "width": table_region.get("width", 0),
                "height": table_region.get("height", 0),
                "page": table_region.get("page", 0),
                "start_idx": table_region["start_idx"],
                "end_idx": table_region["end_idx"]
            })
        
        return tables
    
    def _identify_sections(self, structure: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
        """
        Identify document sections within the document structure.
        
        Args:
            structure: The document structure from the recognition model
            text: The OCR text
            
        Returns:
            List of section structures with content information
        """
        sections = []
        
        # Extract section regions from structure
        for section_region in structure.get("section_regions", []):
            section_text = text[section_region["start_idx"]:section_region["end_idx"]]
            
            # Extract section title if available
            title = ""
            if "title_end_idx" in section_region:
                title = section_text[:section_region["title_end_idx"]].strip()
                content = section_text[section_region["title_end_idx"]:].strip()
            else:
                content = section_text.strip()
            
            sections.append({
                "title": title,
                "content": content,
                "x": section_region.get("x", 0),
                "y": section_region.get("y", 0),
                "width": section_region.get("width", 0),
                "height": section_region.get("height", 0),
                "page": section_region.get("page", 0),
                "start_idx": section_region["start_idx"],
                "end_idx": section_region["end_idx"]
            })
        
        return sections
    
    def _extract_form_fields(self, form: Dict[str, Any], text: str, document_type: str) -> List[ExtractedField]:
        """
        Extract fields from a form structure.
        
        Args:
            form: The form structure
            text: The OCR text
            document_type: The type of document
            
        Returns:
            List of extracted fields from the form
        """
        extracted_fields = []
        
        for field in form.get("fields", []):
            # Calculate confidence based on field clarity
            confidence = self._calculate_field_confidence(field["value"])
            
            # Map field label to standardized name if possible
            field_name = self._map_field_name(field["label"], document_type)
            
            # Create field location
            location = FieldLocation(
                page=field.get("page", 0),
                x=field.get("x", 0),
                y=field.get("y", 0),
                width=field.get("width", 0),
                height=field.get("height", 0)
            )
            
            extracted_fields.append(ExtractedField(
                name=field_name,
                value=field["value"],
                confidence=confidence,
                location=location,
                metadata={
                    "source": "form_extraction",
                    "form_name": form.get("name", "unnamed_form"),
                    "original_label": field["label"] if field_name != field["label"] else None,
                    "section": "form_fields"
                }
            ))
        
        return extracted_fields
    
    def _extract_table_headers(self, header_text: str) -> List[str]:
        """
        Extract column headers from table header text.
        
        Args:
            header_text: The text of the table header row
            
        Returns:
            List of column header names
        """
        # Simple splitting by whitespace for now
        # In a real implementation, this would use more sophisticated parsing
        # based on the table structure recognition
        headers = [h.strip() for h in re.split(r'\s{2,}', header_text) if h.strip()]
        return headers
    
    def _extract_row_data(self, row_text: str, headers: List[str], table_structure: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract data from a table row.
        
        Args:
            row_text: The text of the table row
            headers: The column headers
            table_structure: The table structure information
            
        Returns:
            Dictionary mapping column names to cell values
        """
        row_data = {}
        
        # If we have cell information, use it
        cells = table_structure.get("cells", [])
        if cells:
            for cell in cells:
                if cell.get("column_index", -1) < len(headers):
                    header = headers[cell.get("column_index", 0)]
                    row_data[header] = cell.get("text", "").strip()
        else:
            # Simple splitting by whitespace
            # In a real implementation, this would use more sophisticated parsing
            values = [v.strip() for v in re.split(r'\s{2,}', row_text) if v.strip()]
            
            # Map values to headers
            for i, value in enumerate(values):
                if i < len(headers):
                    row_data[headers[i]] = value
        
        return row_data
    
    def _find_field_location(self, key: str, value: str, text: str) -> FieldLocation:
        """
        Find the approximate location of a field in the document.
        
        Args:
            key: The field key/label
            value: The field value
            text: The OCR text
            
        Returns:
            FieldLocation object with approximate coordinates
        """
        # In a real implementation, this would use the bounding box information
        # from the OCR result to determine the exact location
        # For now, we'll just use a placeholder
        return FieldLocation(
            page=0,
            x=0,
            y=0,
            width=0,
            height=0
        )
    
    def _calculate_key_value_confidence(self, key: str, value: str, document_type: str) -> ConfidenceScore:
        """
        Calculate confidence score for a key-value pair extraction.
        
        Args:
            key: The extracted key
            value: The extracted value
            document_type: The type of document
            
        Returns:
            ConfidenceScore between 0.0 and 1.0
        """
        # Start with a base confidence
        confidence = 0.7
        
        # Adjust based on key characteristics
        if len(key) < 3:
            confidence -= 0.1  # Very short keys are less reliable
        
        # Adjust based on value characteristics
        if not value or len(value) < 2:
            confidence -= 0.2  # Empty or very short values are less reliable
        
        # Check if key matches expected fields for this document type
        template = self.extraction_templates.get(document_type, {})
        if template and key in template.get("field_mapping", {}):
            confidence += 0.2  # Known field increases confidence
        
        # Ensure confidence is within bounds
        confidence = max(0.1, min(0.95, confidence))
        
        return ConfidenceScore(confidence)
    
    def _calculate_pattern_match_confidence(self, match: re.Match, pattern: str) -> ConfidenceScore:
        """
        Calculate confidence score for a regex pattern match.
        
        Args:
            match: The regex match object
            pattern: The regex pattern used
            
        Returns:
            ConfidenceScore between 0.0 and 1.0
        """
        # Start with a base confidence for pattern matches
        confidence = 0.8
        
        # Adjust based on match characteristics
        if match.group(1) and len(match.group(1)) > 3:
            confidence += 0.1  # Longer matches are more reliable
        
        # Adjust based on pattern complexity
        pattern_complexity = len(pattern) / 50  # Normalize by typical pattern length
        confidence += min(0.1, pattern_complexity * 0.1)  # More complex patterns can be more reliable
        
        # Ensure confidence is within bounds
        confidence = max(0.1, min(0.95, confidence))
        
        return ConfidenceScore(confidence)
    
    def _calculate_field_confidence(self, value: str) -> ConfidenceScore:
        """
        Calculate confidence score for a form field value.
        
        Args:
            value: The field value
            
        Returns:
            ConfidenceScore between 0.0 and 1.0
        """
        # Start with a base confidence
        confidence = 0.75
        
        # Adjust based on value characteristics
        if not value:
            confidence = 0.1  # Empty values have very low confidence
        elif len(value) < 2:
            confidence = 0.3  # Very short values have low confidence
        elif len(value) > 50:
            confidence -= 0.1  # Very long values might be less reliable
        
        # Check for common OCR errors (mixed case, special characters)
        if re.search(r'[A-Za-z0-9].*[^A-Za-z0-9\s\.,;:\-\'"]', value):
            confidence -= 0.1  # Unusual character combinations
        
        # Ensure confidence is within bounds
        confidence = max(0.1, min(0.95, confidence))
        
        return ConfidenceScore(confidence)
    
    def _map_field_name(self, label: str, document_type: str) -> str:
        """
        Map a field label to a standardized field name.
        
        Args:
            label: The original field label
            document_type: The type of document
            
        Returns:
            Standardized field name
        """
        # Get document template if available
        template = self.extraction_templates.get(document_type, {})
        field_mapping = template.get("field_mapping", {})
        
        # Check for exact match
        if label in field_mapping:
            return field_mapping[label]
        
        # Check for case-insensitive match
        label_lower = label.lower()
        for key, value in field_mapping.items():
            if key.lower() == label_lower:
                return value
        
        # Check for partial match (if label contains the key)
        for key, value in field_mapping.items():
            if key.lower() in label_lower:
                return value
        
        # No mapping found, use the original label
        return label
    
    def _deduplicate_fields(self, fields: List[ExtractedField]) -> List[ExtractedField]:
        """
        Remove duplicate fields, preferring those with higher confidence.
        
        Args:
            fields: List of extracted fields
            
        Returns:
            Deduplicated list of fields
        """
        # Group fields by name
        field_groups = {}
        for field in fields:
            if field.name not in field_groups:
                field_groups[field.name] = []
            field_groups[field.name].append(field)
        
        # For each group, select the field with highest confidence
        deduplicated = []
        for name, group in field_groups.items():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # Sort by confidence (descending)
                sorted_group = sorted(group, key=lambda f: f.confidence.value, reverse=True)
                deduplicated.append(sorted_group[0])
        
        return deduplicated
    
    def _calculate_average_confidence(self, fields: List[ExtractedField]) -> float:
        """
        Calculate the average confidence score across all fields.
        
        Args:
            fields: List of extracted fields
            
        Returns:
            Average confidence score
        """
        if not fields:
            return 0.0
            
        total_confidence = sum(field.confidence.value for field in fields)
        return total_confidence / len(fields)
    
    def _get_current_timestamp(self) -> str:
        """
        Get the current timestamp in ISO 8601 format.
        
        Returns:
            Current timestamp string
        """
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    def _create_json_schema(self, document_type: str, fields: List[ExtractedField]) -> JSONSchema:
        """
        Create a JSON schema for the extracted data based on document type.
        
        Args:
            document_type: The type of document
            fields: List of extracted fields
            
        Returns:
            JSONSchema object
        """
        # In a real implementation, this would create a proper JSON Schema
        # based on the document type and extracted fields
        # For now, we'll just use a placeholder
        return JSONSchema(
            schema_id=f"mca-{document_type}-schema",
            version="1.0.0",
            schema={}
        )
    
    def _load_extraction_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Load document type-specific extraction templates.
        
        Returns:
            Dictionary mapping document types to extraction templates
        """
        # In a real implementation, these would be loaded from configuration files
        # For now, we'll define them inline
        templates = {
            "loan_application": {
                "field_mapping": {
                    "Business Name": "business_name",
                    "Business Legal Name": "business_legal_name",
                    "DBA": "dba_name",
                    "Tax ID": "tax_id",
                    "EIN": "tax_id",
                    "Federal Tax ID": "tax_id",
                    "Business Address": "business_address",
                    "Business Phone": "business_phone",
                    "Business Email": "business_email",
                    "Years in Business": "years_in_business",
                    "Annual Revenue": "annual_revenue",
                    "Monthly Revenue": "monthly_revenue",
                    "Requested Amount": "requested_amount",
                    "Owner Name": "owner_name",
                    "Owner Address": "owner_address",
                    "Owner Phone": "owner_phone",
                    "Owner Email": "owner_email",
                    "Owner SSN": "owner_ssn",
                    "Date of Birth": "owner_dob",
                    "Credit Score": "credit_score",
                    "Business Type": "business_type",
                    "Industry": "industry"
                }
            },
            "tax_return": {
                "field_mapping": {
                    "Adjusted Gross Income": "adjusted_gross_income",
                    "Total Income": "total_income",
                    "Taxable Income": "taxable_income",
                    "Total Tax": "total_tax",
                    "Federal Income Tax Withheld": "federal_tax_withheld",
                    "Tax Year": "tax_year",
                    "Filing Status": "filing_status",
                    "Taxpayer Name": "taxpayer_name",
                    "Taxpayer SSN": "taxpayer_ssn",
                    "Spouse Name": "spouse_name",
                    "Spouse SSN": "spouse_ssn",
                    "Business Income": "business_income",
                    "Business Expenses": "business_expenses",
                    "Net Profit": "net_profit"
                }
            },
            "bank_statement": {
                "field_mapping": {
                    "Account Number": "account_number",
                    "Account Holder": "account_holder",
                    "Bank Name": "bank_name",
                    "Statement Period": "statement_period",
                    "Beginning Balance": "beginning_balance",
                    "Ending Balance": "ending_balance",
                    "Total Deposits": "total_deposits",
                    "Total Withdrawals": "total_withdrawals",
                    "Average Balance": "average_balance"
                }
            },
            "identity_document": {
                "field_mapping": {
                    "Full Name": "full_name",
                    "First Name": "first_name",
                    "Last Name": "last_name",
                    "Date of Birth": "date_of_birth",
                    "Address": "address",
                    "ID Number": "id_number",
                    "License Number": "license_number",
                    "Expiration Date": "expiration_date",
                    "Issue Date": "issue_date",
                    "State": "state",
                    "Country": "country",
                    "Gender": "gender",
                    "Height": "height",
                    "Eye Color": "eye_color",
                    "Class": "license_class"
                }
            }
        }
        
        return templates
    
    def _load_normalization_rules(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Load field normalization rules.
        
        Returns:
            Dictionary mapping document types to field normalization rules
        """
        # In a real implementation, these would be loaded from configuration files
        # For now, we'll define them inline
        rules = {
            "default": {
                "date_of_birth": {"type": "date", "format": "%Y-%m-%d"},
                "expiration_date": {"type": "date", "format": "%Y-%m-%d"},
                "issue_date": {"type": "date", "format": "%Y-%m-%d"},
                "phone": {"type": "phone", "format": "E.164"},
                "email": {"type": "email"},
                "ssn": {"type": "ssn", "format": "XXX-XX-XXXX"},
                "tax_id": {"type": "tax_id", "format": "XX-XXXXXXX"},
                "amount": {"type": "currency", "format": "USD"},
                "percentage": {"type": "percentage"}
            },
            "loan_application": {
                "business_phone": {"type": "phone", "format": "E.164"},
                "owner_phone": {"type": "phone", "format": "E.164"},
                "business_email": {"type": "email"},
                "owner_email": {"type": "email"},
                "owner_ssn": {"type": "ssn", "format": "XXX-XX-XXXX"},
                "owner_dob": {"type": "date", "format": "%Y-%m-%d"},
                "annual_revenue": {"type": "currency", "format": "USD"},
                "monthly_revenue": {"type": "currency", "format": "USD"},
                "requested_amount": {"type": "currency", "format": "USD"},
                "years_in_business": {"type": "number", "format": "integer"}
            },
            "bank_statement": {
                "beginning_balance": {"type": "currency", "format": "USD"},
                "ending_balance": {"type": "currency", "format": "USD"},
                "total_deposits": {"type": "currency", "format": "USD"},
                "total_withdrawals": {"type": "currency", "format": "USD"},
                "average_balance": {"type": "currency", "format": "USD"},
                "statement_period": {"type": "date_range", "format": "%Y-%m-%d to %Y-%m-%d"}
            }
        }
        
        return rules
    
    def _load_validation_rules(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Load field validation rules.
        
        Returns:
            Dictionary mapping document types to field validation rules
        """
        # In a real implementation, these would be loaded from configuration files
        # For now, we'll define them inline
        rules = {
            "default": {
                "email": {
                    "type": "email",
                    "constraints": {
                        "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                    }
                },
                "phone": {
                    "type": "phone",
                    "constraints": {
                        "min_length": 10,
                        "max_length": 15
                    }
                },
                "date": {
                    "type": "date",
                    "constraints": {
                        "min_date": "1900-01-01",
                        "max_date": "2100-12-31"
                    }
                },
                "currency": {
                    "type": "currency",
                    "constraints": {
                        "min_value": 0,
                        "max_value": 1000000000
                    }
                }
            },
            "loan_application": {
                "tax_id": {
                    "type": "tax_id",
                    "constraints": {
                        "pattern": r"^\d{2}-\d{7}$|^\d{9}$"
                    }
                },
                "owner_ssn": {
                    "type": "ssn",
                    "constraints": {
                        "pattern": r"^\d{3}-\d{2}-\d{4}$|^\d{9}$"
                    }
                },
                "years_in_business": {
                    "type": "number",
                    "constraints": {
                        "min_value": 0,
                        "max_value": 100,
                        "integer": True
                    }
                },
                "requested_amount": {
                    "type": "currency",
                    "constraints": {
                        "min_value": 1000,
                        "max_value": 5000000
                    }
                }
            },
            "bank_statement": {
                "account_number": {
                    "type": "string",
                    "constraints": {
                        "min_length": 4,
                        "max_length": 17,
                        "pattern": r"^[\d\*]+$"
                    }
                }
            }
        }
        
        return rules
    
    def _load_field_patterns(self) -> Dict[str, Dict[str, str]]:
        """
        Load regular expression patterns for field extraction.
        
        Returns:
            Dictionary mapping document types to field patterns
        """
        # In a real implementation, these would be loaded from configuration files
        # For now, we'll define them inline
        patterns = {
            "default": {
                "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "phone": r"\(?(\d{3})\)?[- ]?(\d{3})[- ]?(\d{4})",
                "date": r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})",
                "ssn": r"(\d{3}[-]?\d{2}[-]?\d{4})",
                "currency": r"\$?([\d,]+\.?\d*)"
            },
            "loan_application": {
                "business_name": r"Business\s+Name[:\s]+(.*?)(?=\n|$|\s{2,})",
                "tax_id": r"(?:Tax\s+ID|EIN|Federal\s+Tax\s+ID)[:\s]+(\d{2}[-]?\d{7})",
                "requested_amount": r"(?:Requested|Loan)\s+Amount[:\s]+\$?([\d,]+\.?\d*)",
                "years_in_business": r"Years\s+in\s+Business[:\s]+(\d+)",
                "annual_revenue": r"Annual\s+Revenue[:\s]+\$?([\d,]+\.?\d*)"
            },
            "bank_statement": {
                "account_number": r"Account\s+(?:Number|#)[:\s]+([\d\*]+)",
                "beginning_balance": r"(?:Beginning|Opening)\s+Balance[:\s]+\$?([\d,]+\.?\d*)",
                "ending_balance": r"(?:Ending|Closing)\s+Balance[:\s]+\$?([\d,]+\.?\d*)",
                "statement_period": r"Statement\s+(?:Period|Date)[:\s]+(.*?)(?=\n|$|\s{2,})"
            },
            "tax_return": {
                "adjusted_gross_income": r"Adjusted\s+Gross\s+Income[:\s]+\$?([\d,]+\.?\d*)",
                "total_tax": r"Total\s+Tax[:\s]+\$?([\d,]+\.?\d*)",
                "tax_year": r"Tax\s+Year[:\s]+(\d{4})"
            },
            "identity_document": {
                "license_number": r"(?:License|ID)\s+(?:Number|#)[:\s]+([A-Z0-9]+)",
                "expiration_date": r"(?:Expiration|Exp)\s+Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})",
                "date_of_birth": r"(?:Date\s+of\s+Birth|DOB|Birth\s+Date)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})"
            }
        }
        
        return patterns
    
    # Document-specific extraction methods
    
    def _extract_loan_application_fields(self, text: str, document_structure: Dict[str, Any]) -> List[ExtractedField]:
        """
        Extract fields specific to loan application documents.
        
        Args:
            text: The OCR text
            document_structure: The document structure
            
        Returns:
            List of extracted fields specific to loan applications
        """
        fields = []
        
        # Look for specific sections in the document
        business_info_section = None
        owner_info_section = None
        financial_info_section = None
        
        for section in document_structure.get("sections", []):
            title_lower = section.get("title", "").lower()
            if "business" in title_lower and "information" in title_lower:
                business_info_section = section
            elif "owner" in title_lower and "information" in title_lower:
                owner_info_section = section
            elif "financial" in title_lower and "information" in title_lower:
                financial_info_section = section
        
        # Extract business information
        if business_info_section:
            business_text = business_info_section.get("content", "")
            business_kv_pairs = self.extract_key_value_pairs(business_text, "loan_application")
            
            for key, value, confidence in business_kv_pairs:
                # Map to standardized field name
                field_name = self._map_field_name(key, "loan_application")
                
                fields.append(ExtractedField(
                    name=field_name,
                    value=value,
                    confidence=confidence,
                    location=self._find_field_location(key, value, business_text),
                    metadata={
                        "source": "section_extraction",
                        "section": "business_information",
                        "original_name": key if field_name != key else None
                    }
                ))
        
        # Extract owner information
        if owner_info_section:
            owner_text = owner_info_section.get("content", "")
            owner_kv_pairs = self.extract_key_value_pairs(owner_text, "loan_application")
            
            for key, value, confidence in owner_kv_pairs:
                # Map to standardized field name
                field_name = self._map_field_name(key, "loan_application")
                
                fields.append(ExtractedField(
                    name=field_name,
                    value=value,
                    confidence=confidence,
                    location=self._find_field_location(key, value, owner_text),
                    metadata={
                        "source": "section_extraction",
                        "section": "owner_information",
                        "original_name": key if field_name != key else None
                    }
                ))
        
        # Extract financial information
        if financial_info_section:
            financial_text = financial_info_section.get("content", "")
            financial_kv_pairs = self.extract_key_value_pairs(financial_text, "loan_application")
            
            for key, value, confidence in financial_kv_pairs:
                # Map to standardized field name
                field_name = self._map_field_name(key, "loan_application")
                
                fields.append(ExtractedField(
                    name=field_name,
                    value=value,
                    confidence=confidence,
                    location=self._find_field_location(key, value, financial_text),
                    metadata={
                        "source": "section_extraction",
                        "section": "financial_information",
                        "original_name": key if field_name != key else None
                    }
                ))
        
        return fields
    
    def _extract_tax_return_fields(self, text: str, document_structure: Dict[str, Any]) -> List[ExtractedField]:
        """
        Extract fields specific to tax return documents.
        
        Args:
            text: The OCR text
            document_structure: The document structure
            
        Returns:
            List of extracted fields specific to tax returns
        """
        fields = []
        
        # Extract tax return specific fields using patterns
        patterns = self.field_patterns.get("tax_return", {})
        
        for field_name, pattern in patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                if match.lastindex and match.lastindex >= 1:
                    value = match.group(1).strip()
                    confidence = self._calculate_pattern_match_confidence(match, pattern)
                    
                    fields.append(ExtractedField(
                        name=field_name,
                        value=value,
                        confidence=confidence,
                        location=self._find_field_location(field_name, value, text),
                        metadata={
                            "source": "pattern_extraction",
                            "section": "tax_return",
                            "pattern": pattern
                        }
                    ))
        
        # Look for income tables
        for table in document_structure.get("tables", []):
            table_name = table.get("name", "").lower()
            if "income" in table_name or "revenue" in table_name:
                table_data = self.extract_table_data(table, text)
                if table_data:
                    fields.append(ExtractedField(
                        name="income_table",
                        value=json.dumps(table_data),
                        confidence=ConfidenceScore(0.9),
                        location=FieldLocation(
                            page=table.get("page", 0),
                            x=table.get("x", 0),
                            y=table.get("y", 0),
                            width=table.get("width", 0),
                            height=table.get("height", 0)
                        ),
                        metadata={
                            "source": "table_extraction",
                            "section": "tax_return",
                            "is_table": True,
                            "row_count": len(table_data)
                        }
                    ))
        
        return fields
    
    def _extract_bank_statement_fields(self, text: str, document_structure: Dict[str, Any]) -> List[ExtractedField]:
        """
        Extract fields specific to bank statement documents.
        
        Args:
            text: The OCR text
            document_structure: The document structure
            
        Returns:
            List of extracted fields specific to bank statements
        """
        fields = []
        
        # Extract bank statement specific fields using patterns
        patterns = self.field_patterns.get("bank_statement", {})
        
        for field_name, pattern in patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                if match.lastindex and match.lastindex >= 1:
                    value = match.group(1).strip()
                    confidence = self._calculate_pattern_match_confidence(match, pattern)
                    
                    fields.append(ExtractedField(
                        name=field_name,
                        value=value,
                        confidence=confidence,
                        location=self._find_field_location(field_name, value, text),
                        metadata={
                            "source": "pattern_extraction",
                            "section": "bank_statement",
                            "pattern": pattern
                        }
                    ))
        
        # Look for transaction tables
        for table in document_structure.get("tables", []):
            table_name = table.get("name", "").lower()
            if "transaction" in table_name or "activity" in table_name:
                table_data = self.extract_table_data(table, text)
                if table_data:
                    fields.append(ExtractedField(
                        name="transactions",
                        value=json.dumps(table_data),
                        confidence=ConfidenceScore(0.9),
                        location=FieldLocation(
                            page=table.get("page", 0),
                            x=table.get("x", 0),
                            y=table.get("y", 0),
                            width=table.get("width", 0),
                            height=table.get("height", 0)
                        ),
                        metadata={
                            "source": "table_extraction",
                            "section": "bank_statement",
                            "is_table": True,
                            "row_count": len(table_data)
                        }
                    ))
        
        return fields
    
    def _extract_identity_document_fields(self, text: str, document_structure: Dict[str, Any]) -> List[ExtractedField]:
        """
        Extract fields specific to identity documents.
        
        Args:
            text: The OCR text
            document_structure: The document structure
            
        Returns:
            List of extracted fields specific to identity documents
        """
        fields = []
        
        # Extract identity document specific fields using patterns
        patterns = self.field_patterns.get("identity_document", {})
        
        for field_name, pattern in patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                if match.lastindex and match.lastindex >= 1:
                    value = match.group(1).strip()
                    confidence = self._calculate_pattern_match_confidence(match, pattern)
                    
                    fields.append(ExtractedField(
                        name=field_name,
                        value=value,
                        confidence=confidence,
                        location=self._find_field_location(field_name, value, text),
                        metadata={
                            "source": "pattern_extraction",
                            "section": "identity_document",
                            "pattern": pattern
                        }
                    ))
        
        # Extract name components if full name is present
        full_name = None
        for field in fields:
            if field.name == "full_name":
                full_name = field.value
                break
        
        if full_name:
            # Simple name splitting logic - in a real implementation this would be more sophisticated
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = name_parts[-1]
                
                # Add first name if not already present
                if not any(f.name == "first_name" for f in fields):
                    fields.append(ExtractedField(
                        name="first_name",
                        value=first_name,
                        confidence=ConfidenceScore(0.8),  # Slightly lower confidence for derived fields
                        location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                        metadata={
                            "source": "derived",
                            "derived_from": "full_name",
                            "section": "identity_document"
                        }
                    ))
                
                # Add last name if not already present
                if not any(f.name == "last_name" for f in fields):
                    fields.append(ExtractedField(
                        name="last_name",
                        value=last_name,
                        confidence=ConfidenceScore(0.8),  # Slightly lower confidence for derived fields
                        location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                        metadata={
                            "source": "derived",
                            "derived_from": "full_name",
                            "section": "identity_document"
                        }
                    ))
        
        return fields