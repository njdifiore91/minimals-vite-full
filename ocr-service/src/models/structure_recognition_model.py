#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Structure Recognition Model for OCR Processing

This module implements a TensorFlow model for recognizing and analyzing document structure,
including forms, tables, sections, and field relationships. The model identifies the
semantic structure of documents to provide context for extracted text, which is critical
for understanding the meaning and relationships of extracted data.

The model uses deep learning techniques to identify:
1. Form fields and their labels
2. Table structures and cell relationships
3. Document sections and hierarchies
4. Semantic relationships between document elements

This contextual understanding enables the OCR service to extract data with proper
relationships and meaning, rather than just extracting text without context.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import numpy as np
import tensorflow as tf

from ..types.config import TensorFlowConfig
from ..types.documents import DocumentContent, DocumentMetadata, DocumentType
from ..types.extraction import ConfidenceScore, ExtractedData, ExtractedField, FieldLocation
from ..types.models import ModelParameters, ModelResult
from ..utils.image_utils import crop_image, normalize_image, preprocess_image
from ..utils.logging_utils import get_logger
from ..utils.tensorflow_utils import configure_gpu_memory

from .base_model import BaseOCRModel


logger = get_logger(__name__)


class StructureRecognitionModel(BaseOCRModel):
    """
    TensorFlow model for document structure recognition and analysis.
    
    This model identifies the semantic structure of documents, including forms,
    tables, sections, and field relationships. It provides context for extracted
    text, which is critical for understanding the meaning and relationships of data.
    
    The model uses a combination of convolutional neural networks and transformer
    architectures to identify structural elements and their relationships within
    documents.
    
    Attributes:
        model_path (Path): Path to the TensorFlow model files
        model_name (str): Name of the model for logging and identification
        model_version (str): Version of the model
        config (TensorFlowConfig): Configuration for TensorFlow and GPU settings
        model (tf.saved_model.SavedModel): The loaded TensorFlow model
        parameters (ModelParameters): Model-specific parameters and hyperparameters
        structure_types (List[str]): Types of document structures recognized by the model
        min_confidence_threshold (float): Minimum confidence threshold for structure detection
    """
    
    def __init__(self, 
                 model_path: Union[str, Path], 
                 config: TensorFlowConfig,
                 parameters: Optional[ModelParameters] = None) -> None:
        """
        Initialize the structure recognition model with the specified model path and configuration.
        
        Args:
            model_path: Path to the TensorFlow model files
            config: Configuration for TensorFlow and GPU settings
            parameters: Model-specific parameters and hyperparameters (optional)
        
        Raises:
            ValueError: If the model path does not exist or is invalid
            RuntimeError: If GPU initialization fails
        """
        # Initialize base class with model name
        super().__init__(model_path, "StructureRecognitionModel", config, parameters)
        
        # Define structure types recognized by this model
        self.structure_types = [
            "form_field",
            "form_label",
            "table",
            "table_cell",
            "table_header",
            "section_heading",
            "section_content",
            "list_item",
            "checkbox",
            "signature_field"
        ]
        
        # Set minimum confidence threshold for structure detection
        self.min_confidence_threshold = self.parameters.get(
            "min_confidence_threshold", 0.7
        )
        
        # Load structure recognition specific components
        self._load_structure_components()
        
        logger.info(
            f"Initialized {self.model_name} with {len(self.structure_types)} structure types "
            f"(version: {self.model_version})"
        )
    
    def _load_structure_components(self) -> None:
        """
        Load additional components specific to structure recognition.
        
        This method loads specialized sub-models for specific structure recognition
        tasks such as table detection, form field analysis, and section identification.
        
        Raises:
            RuntimeError: If component loading fails
        """
        try:
            # The main model loaded in the parent class handles the primary structure detection
            # Here we load specialized components if they exist
            
            # Check for table structure model
            table_model_path = self.model_path / "table_structure"
            if table_model_path.exists():
                self.table_model = tf.saved_model.load(str(table_model_path))
                logger.info(f"Loaded table structure model from {table_model_path}")
            else:
                self.table_model = None
                logger.info("No specialized table structure model found")
            
            # Check for form field model
            form_model_path = self.model_path / "form_analysis"
            if form_model_path.exists():
                self.form_model = tf.saved_model.load(str(form_model_path))
                logger.info(f"Loaded form analysis model from {form_model_path}")
            else:
                self.form_model = None
                logger.info("No specialized form analysis model found")
            
            # Check for section identification model
            section_model_path = self.model_path / "section_identification"
            if section_model_path.exists():
                self.section_model = tf.saved_model.load(str(section_model_path))
                logger.info(f"Loaded section identification model from {section_model_path}")
            else:
                self.section_model = None
                logger.info("No specialized section identification model found")
                
        except Exception as e:
            error_msg = f"Failed to load structure recognition components: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def extract_text(self, image: np.ndarray) -> List[Tuple[str, ConfidenceScore]]:
        """
        Extract text from the preprocessed document image.
        
        This implementation focuses on extracting text with structural context,
        identifying text elements based on their role in the document structure.
        
        Args:
            image: Preprocessed document image as a numpy array
            
        Returns:
            List of tuples containing extracted text and confidence scores
            
        Raises:
            RuntimeError: If text extraction fails
        """
        try:
            # Prepare input tensor
            input_tensor = tf.convert_to_tensor(image, dtype=tf.float32)
            input_tensor = tf.expand_dims(input_tensor, 0)  # Add batch dimension
            
            # Run inference for text extraction with structural context
            # The model returns both text and its structural role
            structured_text = self.model.signatures["extract_text"](input_tensor)
            
            # Process results
            text_results = []
            
            # Extract text and confidence scores from the model output
            texts = structured_text["texts"].numpy()[0]
            confidences = structured_text["confidences"].numpy()[0]
            
            # Combine text with confidence scores
            for text, confidence in zip(texts, confidences):
                # Decode text from bytes if necessary
                if isinstance(text, bytes):
                    text = text.decode("utf-8")
                
                # Skip empty text
                if not text.strip():
                    continue
                    
                text_results.append((text, float(confidence)))
            
            return text_results
            
        except Exception as e:
            error_msg = f"Failed to extract text with structure recognition: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def extract_fields(self, image: np.ndarray, 
                      document_metadata: DocumentMetadata) -> List[ExtractedField]:
        """
        Extract structured fields from the document image based on document structure.
        
        This method identifies form fields, table cells, and other structured elements
        in the document, and extracts their values with contextual understanding.
        
        Args:
            image: Preprocessed document image as a numpy array
            document_metadata: Metadata of the document including type and classification
            
        Returns:
            List of extracted fields with values, confidence scores, and structural context
            
        Raises:
            RuntimeError: If field extraction fails
        """
        try:
            # Prepare input tensor
            input_tensor = tf.convert_to_tensor(image, dtype=tf.float32)
            input_tensor = tf.expand_dims(input_tensor, 0)  # Add batch dimension
            
            # Run inference for structure recognition
            structure_result = self.model.signatures["recognize_structure"](input_tensor)
            
            # Extract structure information
            structure_types = structure_result["structure_types"].numpy()[0]
            structure_boxes = structure_result["structure_boxes"].numpy()[0]
            structure_confidences = structure_result["structure_confidences"].numpy()[0]
            
            # Process structure information to identify fields
            extracted_fields = self._process_structure_results(
                structure_types, structure_boxes, structure_confidences, image, document_metadata
            )
            
            # Add relationships between fields based on document structure
            extracted_fields = self._add_field_relationships(extracted_fields)
            
            return extracted_fields
            
        except Exception as e:
            error_msg = f"Failed to extract fields with structure recognition: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _process_structure_results(
        self,
        structure_types: np.ndarray,
        structure_boxes: np.ndarray,
        structure_confidences: np.ndarray,
        image: np.ndarray,
        document_metadata: DocumentMetadata
    ) -> List[ExtractedField]:
        """
        Process structure recognition results to extract fields.
        
        This method converts the raw structure detection results into a list of
        extracted fields with proper values and metadata.
        
        Args:
            structure_types: Array of detected structure type indices
            structure_boxes: Array of bounding boxes for detected structures
            structure_confidences: Array of confidence scores for detected structures
            image: Original preprocessed image
            document_metadata: Metadata of the document
            
        Returns:
            List of extracted fields with values and structural context
        """
        extracted_fields = []
        
        # Get document type for context-aware extraction
        doc_type = document_metadata.document_type or DocumentType.OTHER
        
        # Process each detected structure
        for struct_type_idx, box, confidence in zip(
            structure_types, structure_boxes, structure_confidences
        ):
            # Skip low-confidence detections
            if confidence < self.min_confidence_threshold:
                continue
                
            # Get structure type name
            struct_type = self.structure_types[int(struct_type_idx)]
            
            # Create field location
            location = FieldLocation(
                page=0,  # Assuming single page processing
                top=float(box[0]),
                left=float(box[1]),
                bottom=float(box[2]),
                right=float(box[3])
            )
            
            # Extract field value based on structure type
            field_value, field_confidence = self._extract_field_value(
                image, box, struct_type, doc_type
            )
            
            # Create extracted field
            field = ExtractedField(
                field_id=f"{struct_type}_{len(extracted_fields)}",
                field_name=self._get_field_name(struct_type, box, doc_type),
                value=field_value,
                raw_text=field_value if isinstance(field_value, str) else str(field_value),
                confidence=field_confidence,
                requires_verification=field_confidence < self.config.verification_threshold,
                location=location,
                field_type=self._get_field_type(struct_type),
                metadata={
                    "structure_type": struct_type,
                    "document_type": doc_type.value if hasattr(doc_type, "value") else str(doc_type),
                    "detection_confidence": float(confidence)
                }
            )
            
            extracted_fields.append(field)
        
        return extracted_fields
    
    def _extract_field_value(
        self,
        image: np.ndarray,
        box: np.ndarray,
        structure_type: str,
        document_type: DocumentType
    ) -> Tuple[Any, float]:
        """
        Extract the value of a field based on its structure type and location.
        
        This method crops the field from the image and extracts its value using
        specialized processing based on the structure type.
        
        Args:
            image: Original preprocessed image
            box: Bounding box of the field [top, left, bottom, right]
            structure_type: Type of document structure
            document_type: Type of document
            
        Returns:
            Tuple of (field_value, confidence_score)
        """
        # Crop the field from the image
        field_image = crop_image(
            image, 
            int(box[0] * image.shape[0]),  # top
            int(box[1] * image.shape[1]),  # left
            int(box[2] * image.shape[0]),  # bottom
            int(box[3] * image.shape[1])   # right
        )
        
        # Normalize the cropped image
        field_image = normalize_image(field_image)
        
        # Prepare input tensor
        input_tensor = tf.convert_to_tensor(field_image, dtype=tf.float32)
        input_tensor = tf.expand_dims(input_tensor, 0)  # Add batch dimension
        
        # Extract value based on structure type
        if structure_type == "form_field":
            # Use form field extraction
            if self.form_model is not None:
                result = self.form_model.signatures["extract_value"](input_tensor)
                value = result["value"].numpy()[0]
                confidence = float(result["confidence"].numpy()[0])
                
                # Decode value if it's bytes
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                    
                return value, confidence
            else:
                # Fallback to basic text extraction
                text_results = self.extract_text(field_image)
                if text_results:
                    return text_results[0][0], text_results[0][1]
                return "", 0.0
                
        elif structure_type == "table_cell":
            # Extract cell value
            text_results = self.extract_text(field_image)
            if text_results:
                return text_results[0][0], text_results[0][1]
            return "", 0.0
            
        elif structure_type == "checkbox":
            # Determine if checkbox is checked
            if self.form_model is not None:
                result = self.form_model.signatures["check_checkbox"](input_tensor)
                is_checked = bool(result["is_checked"].numpy()[0])
                confidence = float(result["confidence"].numpy()[0])
                return is_checked, confidence
            else:
                # Simple checkbox detection based on pixel density
                # This is a fallback method and not as accurate as the model-based approach
                gray_image = np.mean(field_image, axis=2) if field_image.ndim > 2 else field_image
                pixel_density = np.sum(gray_image < 0.5) / gray_image.size
                is_checked = pixel_density > 0.2  # Threshold for checked box
                confidence = 0.5 + abs(pixel_density - 0.2) * 2.5  # Simple confidence calculation
                return is_checked, min(confidence, 1.0)
                
        elif structure_type == "signature_field":
            # Check if signature is present
            # This is a simplified approach; a real implementation would use a signature detection model
            gray_image = np.mean(field_image, axis=2) if field_image.ndim > 2 else field_image
            pixel_density = np.sum(gray_image < 0.8) / gray_image.size
            has_signature = pixel_density > 0.05  # Threshold for signature presence
            confidence = 0.5 + pixel_density * 5  # Simple confidence calculation
            return has_signature, min(confidence, 1.0)
            
        else:
            # Default to text extraction for other structure types
            text_results = self.extract_text(field_image)
            if text_results:
                return text_results[0][0], text_results[0][1]
            return "", 0.0
    
    def _get_field_name(self, structure_type: str, box: np.ndarray, document_type: DocumentType) -> str:
        """
        Generate a human-readable name for the field based on its structure type and context.
        
        Args:
            structure_type: Type of document structure
            box: Bounding box of the field
            document_type: Type of document
            
        Returns:
            Human-readable field name
        """
        # Basic field naming based on structure type
        if structure_type == "form_field":
            return "Form Field"
        elif structure_type == "form_label":
            return "Label"
        elif structure_type == "table_cell":
            return "Table Cell"
        elif structure_type == "table_header":
            return "Table Header"
        elif structure_type == "section_heading":
            return "Section Heading"
        elif structure_type == "section_content":
            return "Section Content"
        elif structure_type == "list_item":
            return "List Item"
        elif structure_type == "checkbox":
            return "Checkbox"
        elif structure_type == "signature_field":
            return "Signature Field"
        else:
            return "Unknown Field"
    
    def _get_field_type(self, structure_type: str) -> str:
        """
        Determine the field type based on structure type.
        
        Args:
            structure_type: Type of document structure
            
        Returns:
            Field type string
        """
        if structure_type == "form_field":
            return "text"
        elif structure_type == "form_label":
            return "text"
        elif structure_type == "table_cell":
            return "text"
        elif structure_type == "table_header":
            return "text"
        elif structure_type == "section_heading":
            return "text"
        elif structure_type == "section_content":
            return "text"
        elif structure_type == "list_item":
            return "text"
        elif structure_type == "checkbox":
            return "boolean"
        elif structure_type == "signature_field":
            return "boolean"
        else:
            return "text"
    
    def _add_field_relationships(self, fields: List[ExtractedField]) -> List[ExtractedField]:
        """
        Add relationships between fields based on document structure analysis.
        
        This method identifies relationships such as label-field pairs, table structures,
        and section hierarchies, and adds this information to the field metadata.
        
        Args:
            fields: List of extracted fields
            
        Returns:
            Updated list of fields with relationship information
        """
        # Create a copy of the fields to avoid modifying the original list
        updated_fields = fields.copy()
        
        # Find form label-field pairs
        self._link_labels_to_fields(updated_fields)
        
        # Identify table structures
        self._identify_table_structures(updated_fields)
        
        # Establish section hierarchies
        self._establish_section_hierarchies(updated_fields)
        
        return updated_fields
    
    def _link_labels_to_fields(self, fields: List[ExtractedField]) -> None:
        """
        Link form labels to their corresponding fields.
        
        This method identifies label-field pairs based on proximity and alignment,
        and updates the field metadata with label information.
        
        Args:
            fields: List of extracted fields to update in-place
        """
        # Separate labels and form fields
        labels = [f for f in fields if f["metadata"]["structure_type"] == "form_label"]
        form_fields = [f for f in fields if f["metadata"]["structure_type"] == "form_field"]
        
        # For each label, find the closest form field
        for label in labels:
            label_loc = label["location"]
            label_center_x = (label_loc["left"] + label_loc["right"]) / 2
            label_center_y = (label_loc["top"] + label_loc["bottom"]) / 2
            
            best_distance = float('inf')
            best_field = None
            
            for field in form_fields:
                field_loc = field["location"]
                field_center_x = (field_loc["left"] + field_loc["right"]) / 2
                field_center_y = (field_loc["top"] + field_loc["bottom"]) / 2
                
                # Calculate distance (prioritize horizontal or vertical alignment)
                if abs(label_center_y - field_center_y) < 0.05:  # Horizontally aligned
                    distance = abs(field_loc["left"] - label_loc["right"])
                elif abs(label_center_x - field_center_x) < 0.05:  # Vertically aligned
                    distance = abs(field_loc["top"] - label_loc["bottom"])
                else:  # Use Euclidean distance
                    distance = ((field_center_x - label_center_x) ** 2 + 
                               (field_center_y - label_center_y) ** 2) ** 0.5
                
                # Update best match if this is closer
                if distance < best_distance and distance < 0.2:  # Threshold for matching
                    best_distance = distance
                    best_field = field
            
            # Link the label to the field
            if best_field is not None:
                # Update field metadata with label information
                if "relationships" not in best_field["metadata"]:
                    best_field["metadata"]["relationships"] = {}
                    
                best_field["metadata"]["relationships"]["label"] = {
                    "field_id": label["field_id"],
                    "value": label["value"]
                }
                
                # Update field name based on label
                if isinstance(label["value"], str) and label["value"].strip():
                    best_field["field_name"] = label["value"].strip()
    
    def _identify_table_structures(self, fields: List[ExtractedField]) -> None:
        """
        Identify table structures and cell relationships.
        
        This method groups table cells into tables, identifies headers and rows,
        and updates the field metadata with table structure information.
        
        Args:
            fields: List of extracted fields to update in-place
        """
        # Get all table-related fields
        table_cells = [f for f in fields if f["metadata"]["structure_type"] == "table_cell"]
        table_headers = [f for f in fields if f["metadata"]["structure_type"] == "table_header"]
        
        if not table_cells and not table_headers:
            return  # No table elements found
        
        # Combine all table elements
        table_elements = table_cells + table_headers
        
        # Group cells into tables based on proximity and alignment
        tables = self._group_cells_into_tables(table_elements)
        
        # For each table, identify rows and columns
        for table_idx, table_cells in enumerate(tables):
            # Sort cells by position (top to bottom, left to right)
            sorted_cells = sorted(table_cells, key=lambda f: (f["location"]["top"], f["location"]["left"]))
            
            # Identify rows based on vertical position
            rows = self._group_cells_into_rows(sorted_cells)
            
            # Identify columns based on horizontal position
            columns = self._group_cells_into_columns(sorted_cells)
            
            # Update each cell with its table, row, and column information
            for cell in sorted_cells:
                # Find row and column indices
                row_idx = next(i for i, row in enumerate(rows) if cell in row)
                col_idx = next(i for i, col in enumerate(columns) if cell in col)
                
                # Update cell metadata
                if "relationships" not in cell["metadata"]:
                    cell["metadata"]["relationships"] = {}
                    
                cell["metadata"]["relationships"]["table"] = {
                    "table_id": f"table_{table_idx}",
                    "row": row_idx,
                    "column": col_idx,
                    "is_header": cell["metadata"]["structure_type"] == "table_header"
                }
                
                # If this is a header cell, link it to all cells in its column
                if cell["metadata"]["structure_type"] == "table_header":
                    # Find all cells in this column
                    column_cells = columns[col_idx]
                    
                    # Update each cell in the column with header information
                    for col_cell in column_cells:
                        if col_cell != cell:  # Skip the header itself
                            if "relationships" not in col_cell["metadata"]:
                                col_cell["metadata"]["relationships"] = {}
                                
                            if "header" not in col_cell["metadata"]["relationships"]:
                                col_cell["metadata"]["relationships"]["header"] = []
                                
                            col_cell["metadata"]["relationships"]["header"].append({
                                "field_id": cell["field_id"],
                                "value": cell["value"]
                            })
    
    def _group_cells_into_tables(self, cells: List[ExtractedField]) -> List[List[ExtractedField]]:
        """
        Group table cells into separate tables based on proximity and alignment.
        
        Args:
            cells: List of table cells and headers
            
        Returns:
            List of tables, where each table is a list of cells
        """
        if not cells:
            return []
            
        # Start with each cell in its own group
        tables = [[cell] for cell in cells]
        
        # Iteratively merge tables that are close to each other
        merged = True
        while merged:
            merged = False
            for i in range(len(tables)):
                if i >= len(tables):
                    continue  # Skip if this table was merged
                    
                for j in range(i + 1, len(tables)):
                    if j >= len(tables):
                        continue  # Skip if this table was merged
                        
                    # Check if tables i and j should be merged
                    if self._should_merge_tables(tables[i], tables[j]):
                        # Merge table j into table i
                        tables[i].extend(tables[j])
                        # Remove table j
                        tables.pop(j)
                        merged = True
                        break
        
        return tables
    
    def _should_merge_tables(self, table1: List[ExtractedField], table2: List[ExtractedField]) -> bool:
        """
        Determine if two tables should be merged based on proximity and alignment.
        
        Args:
            table1: First table (list of cells)
            table2: Second table (list of cells)
            
        Returns:
            True if tables should be merged, False otherwise
        """
        # Calculate bounding box for each table
        table1_bbox = self._get_table_bbox(table1)
        table2_bbox = self._get_table_bbox(table2)
        
        # Check if tables overlap or are very close
        horizontal_overlap = (
            table1_bbox["left"] <= table2_bbox["right"] and
            table2_bbox["left"] <= table1_bbox["right"]
        )
        
        vertical_overlap = (
            table1_bbox["top"] <= table2_bbox["bottom"] and
            table2_bbox["top"] <= table1_bbox["bottom"]
        )
        
        # Calculate distance between tables
        if horizontal_overlap:
            horizontal_distance = 0
        else:
            horizontal_distance = min(
                abs(table1_bbox["left"] - table2_bbox["right"]),
                abs(table2_bbox["left"] - table1_bbox["right"])
            )
            
        if vertical_overlap:
            vertical_distance = 0
        else:
            vertical_distance = min(
                abs(table1_bbox["top"] - table2_bbox["bottom"]),
                abs(table2_bbox["top"] - table1_bbox["bottom"])
            )
        
        # Merge if tables overlap or are very close
        return (horizontal_overlap and vertical_overlap) or (
            horizontal_distance < 0.05 and vertical_overlap) or (
            vertical_distance < 0.05 and horizontal_overlap)
    
    def _get_table_bbox(self, table: List[ExtractedField]) -> Dict[str, float]:
        """
        Calculate the bounding box for a table.
        
        Args:
            table: List of cells in the table
            
        Returns:
            Dictionary with top, left, bottom, right coordinates
        """
        if not table:
            return {"top": 0, "left": 0, "bottom": 0, "right": 0}
            
        # Initialize with the first cell
        bbox = {
            "top": table[0]["location"]["top"],
            "left": table[0]["location"]["left"],
            "bottom": table[0]["location"]["bottom"],
            "right": table[0]["location"]["right"]
        }
        
        # Expand bbox to include all cells
        for cell in table[1:]:
            bbox["top"] = min(bbox["top"], cell["location"]["top"])
            bbox["left"] = min(bbox["left"], cell["location"]["left"])
            bbox["bottom"] = max(bbox["bottom"], cell["location"]["bottom"])
            bbox["right"] = max(bbox["right"], cell["location"]["right"])
            
        return bbox
    
    def _group_cells_into_rows(self, cells: List[ExtractedField]) -> List[List[ExtractedField]]:
        """
        Group table cells into rows based on vertical position.
        
        Args:
            cells: List of table cells
            
        Returns:
            List of rows, where each row is a list of cells
        """
        if not cells:
            return []
            
        # Sort cells by vertical position
        sorted_cells = sorted(cells, key=lambda f: f["location"]["top"])
        
        rows = []
        current_row = [sorted_cells[0]]
        current_row_bottom = sorted_cells[0]["location"]["bottom"]
        
        # Group cells into rows
        for cell in sorted_cells[1:]:
            # If this cell overlaps vertically with the current row, add it to the row
            if cell["location"]["top"] <= current_row_bottom + 0.02:  # Small tolerance
                current_row.append(cell)
                current_row_bottom = max(current_row_bottom, cell["location"]["bottom"])
            else:
                # Start a new row
                rows.append(current_row)
                current_row = [cell]
                current_row_bottom = cell["location"]["bottom"]
        
        # Add the last row
        if current_row:
            rows.append(current_row)
            
        # Sort cells within each row by horizontal position
        for i in range(len(rows)):
            rows[i] = sorted(rows[i], key=lambda f: f["location"]["left"])
            
        return rows
    
    def _group_cells_into_columns(self, cells: List[ExtractedField]) -> List[List[ExtractedField]]:
        """
        Group table cells into columns based on horizontal position.
        
        Args:
            cells: List of table cells
            
        Returns:
            List of columns, where each column is a list of cells
        """
        if not cells:
            return []
            
        # Sort cells by horizontal position
        sorted_cells = sorted(cells, key=lambda f: f["location"]["left"])
        
        columns = []
        current_column = [sorted_cells[0]]
        current_column_right = sorted_cells[0]["location"]["right"]
        
        # Group cells into columns
        for cell in sorted_cells[1:]:
            # If this cell overlaps horizontally with the current column, add it to the column
            if cell["location"]["left"] <= current_column_right + 0.02:  # Small tolerance
                current_column.append(cell)
                current_column_right = max(current_column_right, cell["location"]["right"])
            else:
                # Start a new column
                columns.append(current_column)
                current_column = [cell]
                current_column_right = cell["location"]["right"]
        
        # Add the last column
        if current_column:
            columns.append(current_column)
            
        # Sort cells within each column by vertical position
        for i in range(len(columns)):
            columns[i] = sorted(columns[i], key=lambda f: f["location"]["top"])
            
        return columns
    
    def _establish_section_hierarchies(self, fields: List[ExtractedField]) -> None:
        """
        Establish hierarchical relationships between document sections.
        
        This method identifies section headings and their content, and updates
        the field metadata with section hierarchy information.
        
        Args:
            fields: List of extracted fields to update in-place
        """
        # Get all section-related fields
        section_headings = [f for f in fields if f["metadata"]["structure_type"] == "section_heading"]
        section_contents = [f for f in fields if f["metadata"]["structure_type"] == "section_content"]
        
        if not section_headings:
            return  # No section headings found
        
        # Sort headings by vertical position
        sorted_headings = sorted(section_headings, key=lambda f: f["location"]["top"])
        
        # For each heading, find its content and subsections
        for i, heading in enumerate(sorted_headings):
            # Find the vertical range for this section
            section_start = heading["location"]["bottom"]
            section_end = float('inf') if i == len(sorted_headings) - 1 else sorted_headings[i+1]["location"]["top"]
            
            # Find content that belongs to this section
            section_content = []
            for content in section_contents:
                content_top = content["location"]["top"]
                if section_start <= content_top < section_end:
                    section_content.append(content)
            
            # Find subsections that belong to this section
            subsections = []
            for j, subheading in enumerate(sorted_headings):
                if i != j:  # Skip the current heading
                    subheading_top = subheading["location"]["top"]
                    if section_start <= subheading_top < section_end:
                        subsections.append(subheading)
            
            # Update heading metadata with section information
            if "relationships" not in heading["metadata"]:
                heading["metadata"]["relationships"] = {}
                
            heading["metadata"]["relationships"]["section"] = {
                "content": [content["field_id"] for content in section_content],
                "subsections": [subheading["field_id"] for subheading in subsections]
            }
            
            # Update content metadata with section information
            for content in section_content:
                if "relationships" not in content["metadata"]:
                    content["metadata"]["relationships"] = {}
                    
                content["metadata"]["relationships"]["section"] = {
                    "heading": heading["field_id"],
                    "heading_text": heading["value"]
                }
            
            # Update subsection metadata with parent section information
            for subheading in subsections:
                if "relationships" not in subheading["metadata"]:
                    subheading["metadata"]["relationships"] = {}
                    
                subheading["metadata"]["relationships"]["parent_section"] = {
                    "heading": heading["field_id"],
                    "heading_text": heading["value"]
                }
    
    def analyze_document_structure(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Perform comprehensive document structure analysis.
        
        This method analyzes the document structure and returns a structured
        representation of the document, including forms, tables, and sections.
        
        Args:
            image: Preprocessed document image as a numpy array
            
        Returns:
            Dictionary containing structured document representation
            
        Raises:
            RuntimeError: If structure analysis fails
        """
        try:
            # Prepare input tensor
            input_tensor = tf.convert_to_tensor(image, dtype=tf.float32)
            input_tensor = tf.expand_dims(input_tensor, 0)  # Add batch dimension
            
            # Run inference for structure analysis
            if "analyze_structure" in self.model.signatures:
                structure_analysis = self.model.signatures["analyze_structure"](input_tensor)
                
                # Process structure analysis results
                document_structure = {
                    "document_type": structure_analysis["document_type"].numpy()[0].decode("utf-8"),
                    "confidence": float(structure_analysis["confidence"].numpy()[0]),
                    "structures": self._process_structure_analysis(structure_analysis)
                }
                
                return document_structure
            else:
                # Fallback to basic structure recognition
                logger.warning("analyze_structure signature not found, falling back to basic recognition")
                
                # Extract fields to get structure information
                dummy_metadata = DocumentMetadata(
                    filename="temp.jpg",
                    size=0,
                    mime_type="image/jpeg"
                )
                
                fields = self.extract_fields(image, dummy_metadata)
                
                # Group fields by structure type
                structures = {}
                for field in fields:
                    struct_type = field["metadata"]["structure_type"]
                    if struct_type not in structures:
                        structures[struct_type] = []
                    structures[struct_type].append({
                        "id": field["field_id"],
                        "value": field["value"],
                        "confidence": field["confidence"],
                        "location": field["location"]
                    })
                
                return {
                    "document_type": "unknown",
                    "confidence": 0.7,  # Default confidence
                    "structures": structures
                }
                
        except Exception as e:
            error_msg = f"Failed to analyze document structure: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _process_structure_analysis(self, analysis_result: Dict[str, tf.Tensor]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process structure analysis results into a structured format.
        
        Args:
            analysis_result: Raw structure analysis results from the model
            
        Returns:
            Dictionary mapping structure types to lists of structure objects
        """
        structures = {}
        
        # Process each structure type
        for struct_type in self.structure_types:
            # Check if this structure type is in the results
            if f"{struct_type}_count" in analysis_result:
                count = int(analysis_result[f"{struct_type}_count"].numpy()[0])
                
                if count > 0:
                    structures[struct_type] = []
                    
                    # Extract information for each instance of this structure type
                    for i in range(count):
                        struct_info = {
                            "id": f"{struct_type}_{i}",
                            "confidence": float(analysis_result[f"{struct_type}_confidences"].numpy()[0][i]),
                            "location": {
                                "page": 0,  # Assuming single page processing
                                "top": float(analysis_result[f"{struct_type}_boxes"].numpy()[0][i][0]),
                                "left": float(analysis_result[f"{struct_type}_boxes"].numpy()[0][i][1]),
                                "bottom": float(analysis_result[f"{struct_type}_boxes"].numpy()[0][i][2]),
                                "right": float(analysis_result[f"{struct_type}_boxes"].numpy()[0][i][3])
                            }
                        }
                        
                        # Add value if available
                        if f"{struct_type}_values" in analysis_result:
                            value = analysis_result[f"{struct_type}_values"].numpy()[0][i]
                            if isinstance(value, bytes):
                                value = value.decode("utf-8")
                            struct_info["value"] = value
                        
                        structures[struct_type].append(struct_info)
        
        return structures
    
    def process_document(self, document_content: DocumentContent, 
                        document_metadata: DocumentMetadata) -> ModelResult:
        """
        Process a document to extract text, fields, and structure information.
        
        This method extends the base class implementation to include document
        structure analysis in the results.
        
        Args:
            document_content: Binary content of the document
            document_metadata: Metadata of the document
            
        Returns:
            ModelResult containing extracted data, structure information, and processing metadata
            
        Raises:
            ValueError: If document processing fails
        """
        # Call the base class implementation for basic processing
        result = super().process_document(document_content, document_metadata)
        
        # If processing was successful, add structure information
        if result.success and result.data is not None:
            try:
                # Get the preprocessed image
                preprocessed_image = self.preprocess_document(document_content, document_metadata)
                
                # Analyze document structure
                structure_info = self.analyze_document_structure(preprocessed_image)
                
                # Add structure information to the result metadata
                if "metadata" not in result.data:
                    result.data["metadata"] = {}
                    
                result.data["metadata"]["document_structure"] = structure_info
                
                logger.info(
                    f"Successfully analyzed document structure for {document_metadata.get('id', '')} "
                    f"(document type: {structure_info['document_type']})"
                )
                
            except Exception as e:
                # Log the error but don't fail the entire processing
                logger.error(f"Failed to add structure information: {str(e)}")
                
                # Add error information to the result
                if "metadata" not in result.data:
                    result.data["metadata"] = {}
                    
                result.data["metadata"]["structure_analysis_error"] = str(e)
        
        return result