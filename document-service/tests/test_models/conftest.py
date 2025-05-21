import os
import pytest
import numpy as np
import pandas as pd
import joblib
import pickle
from typing import Dict, List, Tuple, Any, Optional, Union, Callable
from unittest.mock import MagicMock, patch
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_curve, auc
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.pipeline import Pipeline

# Define document types for testing
DOCUMENT_TYPES = [
    'application_form',
    'bank_statement',
    'tax_return',
    'identity_document',
    'business_license',
    'invoice',
    'utility_bill',
    'credit_report'
]

# Define document categories for classification
DOCUMENT_CATEGORIES = {
    'financial': ['bank_statement', 'tax_return', 'invoice', 'credit_report'],
    'identity': ['identity_document', 'business_license'],
    'application': ['application_form'],
    'utility': ['utility_bill']
}

# Define sample document content for each type
SAMPLE_DOCUMENT_CONTENT = {
    'application_form': "This is a merchant cash advance application form for Dollar Funding. Business Name: ABC Corp. Owner: John Smith. Amount Requested: $50,000. Business Address: 123 Main St, Los Angeles, CA 90001. Tax ID: 12-3456789. Years in Business: 5.",
    'bank_statement': "BANK STATEMENT Account: 12345678 Balance: $10,000.00 Account Holder: ABC Corp. Statement Period: 01/01/2023 - 01/31/2023. Deposits: $25,000.00. Withdrawals: $15,000.00. Previous Balance: $0.00. Ending Balance: $10,000.00.",
    'tax_return': "FORM 1040 U.S. Individual Income Tax Return 2023. Taxpayer: John Smith. SSN: XXX-XX-1234. Filing Status: Single. Income: $120,000. Deductions: $24,000. Taxable Income: $96,000. Tax: $21,000. Refund: $2,500.",
    'identity_document': "DRIVER LICENSE STATE OF CALIFORNIA. Name: JOHN SMITH. Address: 123 MAIN ST, LOS ANGELES, CA 90001. DOB: 01/01/1980. Sex: M. Height: 5'10\". Eyes: BRN. License #: D1234567. Expires: 01/01/2025.",
    'business_license': "BUSINESS LICENSE City of Los Angeles Business Tax Registration Certificate. Business Name: ABC Corp. Business Address: 123 Main St, Los Angeles, CA 90001. License #: BL-12345. Issue Date: 01/01/2023. Expiration Date: 12/31/2023. Business Type: Retail.",
    'invoice': "INVOICE #12345 Amount Due: $5,000.00. Bill To: XYZ Company. Address: 456 Oak St, San Francisco, CA 94101. Date: 02/15/2023. Due Date: 03/15/2023. Description: Consulting Services. Quantity: 50 hours. Rate: $100/hr. Total: $5,000.00.",
    'utility_bill': "ELECTRIC BILL Account: 87654321 Amount Due: $150.00. Customer: ABC Corp. Service Address: 123 Main St, Los Angeles, CA 90001. Billing Period: 01/01/2023 - 01/31/2023. Previous Reading: 5000 kWh. Current Reading: 6000 kWh. Usage: 1000 kWh. Rate: $0.15/kWh.",
    'credit_report': "CREDIT REPORT Credit Score: 750 Excellent. Name: John Smith. SSN: XXX-XX-1234. Report Date: 03/01/2023. Accounts: 5. Open Accounts: 3. Closed Accounts: 2. Derogatory Marks: 0. Hard Inquiries: 2. Credit Utilization: 15%."
}

# Define document features for classification
DOCUMENT_FEATURES = {
    'application_form': ['merchant cash advance', 'application', 'business name', 'owner', 'amount requested', 'tax id'],
    'bank_statement': ['bank statement', 'account', 'balance', 'deposits', 'withdrawals', 'statement period'],
    'tax_return': ['tax return', 'form 1040', 'income', 'deductions', 'taxable income', 'refund'],
    'identity_document': ['driver license', 'state', 'name', 'address', 'dob', 'expires'],
    'business_license': ['business license', 'tax registration', 'certificate', 'business name', 'license #'],
    'invoice': ['invoice', 'amount due', 'bill to', 'description', 'quantity', 'rate', 'total'],
    'utility_bill': ['electric bill', 'account', 'service address', 'billing period', 'usage', 'rate'],
    'credit_report': ['credit report', 'credit score', 'accounts', 'derogatory marks', 'inquiries', 'utilization']
}


@pytest.fixture
def document_types() -> List[str]:
    """Return a list of document types used for testing."""
    return DOCUMENT_TYPES


@pytest.fixture
def document_categories() -> Dict[str, List[str]]:
    """Return a dictionary mapping categories to document types."""
    return DOCUMENT_CATEGORIES


@pytest.fixture
def document_features_dict() -> Dict[str, List[str]]:
    """Return a dictionary of key features for each document type."""
    return DOCUMENT_FEATURES


@pytest.fixture
def sample_document_content() -> Dict[str, str]:
    """Return a dictionary of sample document content for each document type."""
    return SAMPLE_DOCUMENT_CONTENT


@pytest.fixture
def sample_documents(document_types, sample_document_content) -> List[Dict[str, Any]]:
    """Generate a list of sample documents for testing.
    
    Each document is a dictionary with the following keys:
    - id: A unique identifier for the document
    - content: The text content of the document
    - type: The document type
    - metadata: Additional metadata about the document
    """
    documents = []
    for i, doc_type in enumerate(document_types):
        documents.append({
            'id': f'doc_{i}',
            'content': sample_document_content[doc_type],
            'type': doc_type,
            'metadata': {
                'page_count': np.random.randint(1, 10),
                'file_size': np.random.randint(100000, 5000000),
                'created_at': pd.Timestamp.now().isoformat(),
                'mime_type': 'application/pdf' if np.random.random() > 0.3 else 'image/jpeg'
            }
        })
    return documents


@pytest.fixture
def tfidf_vectorizer() -> TfidfVectorizer:
    """Return a TF-IDF vectorizer for feature extraction."""
    return TfidfVectorizer(
        max_features=100,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.9
    )


@pytest.fixture
def count_vectorizer() -> CountVectorizer:
    """Return a Count vectorizer for feature extraction."""
    return CountVectorizer(
        max_features=100,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.9
    )


@pytest.fixture
def feature_extraction_pipeline() -> Pipeline:
    """Return a scikit-learn pipeline for feature extraction and preprocessing."""
    return Pipeline([
        ('vectorizer', TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )),
        ('scaler', StandardScaler(with_mean=False)),  # with_mean=False for sparse matrices
        ('dim_reduction', TruncatedSVD(n_components=50))
    ])


@pytest.fixture
def document_features(sample_documents, tfidf_vectorizer) -> Tuple[np.ndarray, List[str]]:
    """Extract features from sample documents using TF-IDF vectorization.
    
    Returns:
        Tuple containing:
        - Feature matrix as a numpy array
        - List of document types (labels)
    """
    # Extract document content and types
    contents = [doc['content'] for doc in sample_documents]
    types = [doc['type'] for doc in sample_documents]
    
    # Fit and transform the document content to create feature vectors
    X = tfidf_vectorizer.fit_transform(contents).toarray()
    
    return X, types


@pytest.fixture
def document_features_pipeline(sample_documents, feature_extraction_pipeline) -> Tuple[np.ndarray, List[str]]:
    """Extract features from sample documents using the feature extraction pipeline.
    
    Returns:
        Tuple containing:
        - Feature matrix as a numpy array
        - List of document types (labels)
    """
    # Extract document content and types
    contents = [doc['content'] for doc in sample_documents]
    types = [doc['type'] for doc in sample_documents]
    
    # Fit and transform the document content to create feature vectors
    X = feature_extraction_pipeline.fit_transform(contents)
    
    return X, types


@pytest.fixture
def document_metadata_features(sample_documents) -> Tuple[np.ndarray, List[str]]:
    """Extract metadata features from sample documents.
    
    Returns:
        Tuple containing:
        - Feature matrix as a numpy array (metadata features only)
        - List of document types (labels)
    """
    # Extract document types and metadata features
    types = [doc['type'] for doc in sample_documents]
    
    # Create metadata feature matrix
    features = np.array([
        [
            doc['metadata']['page_count'],
            doc['metadata']['file_size'],
            1 if doc['metadata']['mime_type'] == 'application/pdf' else 0,
            len(doc['content'].split())
        ]
        for doc in sample_documents
    ])
    
    return features, types


@pytest.fixture
def train_test_data(document_features) -> Tuple[np.ndarray, np.ndarray, List[str], List[str]]:
    """Split document features into training and testing sets.
    
    Returns:
        Tuple containing:
        - X_train: Training feature matrix
        - X_test: Testing feature matrix
        - y_train: Training labels
        - y_test: Testing labels
    """
    X, y = document_features
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    return X_train, X_test, y_train, y_test


@pytest.fixture
def mock_svm_classifier() -> MagicMock:
    """Create a mock SVM classifier for testing."""
    mock_svm = MagicMock(spec=SVC)
    mock_svm.predict.return_value = [DOCUMENT_TYPES[0], DOCUMENT_TYPES[1], DOCUMENT_TYPES[2]]
    mock_svm.predict_proba.return_value = np.array([
        [0.8, 0.1, 0.05, 0.02, 0.01, 0.01, 0.005, 0.005],
        [0.1, 0.75, 0.05, 0.05, 0.02, 0.01, 0.01, 0.01],
        [0.05, 0.05, 0.8, 0.03, 0.02, 0.02, 0.02, 0.01]
    ])
    return mock_svm


@pytest.fixture
def mock_random_forest_classifier() -> MagicMock:
    """Create a mock Random Forest classifier for testing."""
    mock_rf = MagicMock(spec=RandomForestClassifier)
    mock_rf.predict.return_value = [DOCUMENT_TYPES[0], DOCUMENT_TYPES[1], DOCUMENT_TYPES[2]]
    mock_rf.predict_proba.return_value = np.array([
        [0.75, 0.15, 0.05, 0.02, 0.01, 0.01, 0.005, 0.005],
        [0.15, 0.7, 0.05, 0.05, 0.02, 0.01, 0.01, 0.01],
        [0.05, 0.05, 0.75, 0.05, 0.03, 0.03, 0.02, 0.02]
    ])
    mock_rf.feature_importances_ = np.random.random(100)
    return mock_rf


@pytest.fixture
def svm_classifier_config() -> Dict[str, Any]:
    """Return configuration parameters for SVM classifier."""
    return {
        'probability': True,
        'kernel': 'linear',
        'C': 1.0,
        'gamma': 'scale',
        'class_weight': 'balanced',
        'random_state': 42
    }


@pytest.fixture
def random_forest_classifier_config() -> Dict[str, Any]:
    """Return configuration parameters for Random Forest classifier."""
    return {
        'n_estimators': 100,
        'max_depth': 10,
        'min_samples_split': 2,
        'min_samples_leaf': 1,
        'class_weight': 'balanced',
        'bootstrap': True,
        'oob_score': True,
        'random_state': 42
    }


@pytest.fixture
def trained_svm_classifier(train_test_data, svm_classifier_config) -> SVC:
    """Create and train a real SVM classifier for testing."""
    X_train, _, y_train, _ = train_test_data
    classifier = SVC(**svm_classifier_config)
    classifier.fit(X_train, y_train)
    return classifier


@pytest.fixture
def trained_random_forest_classifier(train_test_data, random_forest_classifier_config) -> RandomForestClassifier:
    """Create and train a real Random Forest classifier for testing."""
    X_train, _, y_train, _ = train_test_data
    classifier = RandomForestClassifier(**random_forest_classifier_config)
    classifier.fit(X_train, y_train)
    return classifier


@pytest.fixture
def cross_validation_results(document_features, svm_classifier_config, random_forest_classifier_config) -> Dict[str, List[float]]:
    """Generate cross-validation results for SVM and Random Forest classifiers.
    
    Returns:
        Dictionary mapping classifier names to lists of cross-validation scores
    """
    X, y = document_features
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    svm = SVC(**svm_classifier_config)
    rf = RandomForestClassifier(**random_forest_classifier_config)
    
    svm_scores = cross_val_score(svm, X, y, cv=cv, scoring='accuracy')
    rf_scores = cross_val_score(rf, X, y, cv=cv, scoring='accuracy')
    
    return {
        'svm': svm_scores.tolist(),
        'random_forest': rf_scores.tolist()
    }


@pytest.fixture
def evaluation_metrics() -> Dict[str, Callable]:
    """Return a dictionary of evaluation metrics for model assessment."""
    return {
        'accuracy': accuracy_score,
        'precision': lambda y_true, y_pred: precision_score(y_true, y_pred, average='weighted'),
        'recall': lambda y_true, y_pred: recall_score(y_true, y_pred, average='weighted'),
        'f1': lambda y_true, y_pred: f1_score(y_true, y_pred, average='weighted')
    }


@pytest.fixture
def confusion_matrix_generator():
    """Factory fixture to generate confusion matrices for model evaluation."""
    def _generate_confusion_matrix(y_true, y_pred, labels=None) -> np.ndarray:
        """Generate a confusion matrix for the given true and predicted labels.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            labels: List of label names (optional)
            
        Returns:
            Confusion matrix as a numpy array
        """
        return confusion_matrix(y_true, y_pred, labels=labels)
    
    return _generate_confusion_matrix


@pytest.fixture
def roc_curve_generator():
    """Factory fixture to generate ROC curves for binary classification."""
    def _generate_roc_curve(y_true, y_score, pos_label=None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate ROC curve data points.
        
        Args:
            y_true: True binary labels
            y_score: Target scores (probabilities for the positive class)
            pos_label: Label of the positive class
            
        Returns:
            Tuple of (false positive rates, true positive rates, thresholds)
        """
        return roc_curve(y_true, y_score, pos_label=pos_label)
    
    return _generate_roc_curve


@pytest.fixture
def auc_calculator():
    """Factory fixture to calculate Area Under the ROC Curve (AUC)."""
    def _calculate_auc(fpr, tpr) -> float:
        """Calculate the Area Under the ROC Curve.
        
        Args:
            fpr: False positive rates
            tpr: True positive rates
            
        Returns:
            AUC score
        """
        return auc(fpr, tpr)
    
    return _calculate_auc


@pytest.fixture
def mock_document_classifier() -> MagicMock:
    """Create a mock DocumentClassifier for testing."""
    mock_classifier = MagicMock()
    mock_classifier.classify.return_value = {
        'document_type': DOCUMENT_TYPES[0],
        'confidence': 0.85,
        'probabilities': {
            doc_type: 0.85 if doc_type == DOCUMENT_TYPES[0] else 0.15 / (len(DOCUMENT_TYPES) - 1)
            for doc_type in DOCUMENT_TYPES
        },
        'processing_time': 0.05,
        'metadata': {
            'model_version': '1.0.0',
            'feature_count': 100,
            'threshold': 0.5
        }
    }
    return mock_classifier


@pytest.fixture
def mock_base_model() -> MagicMock:
    """Create a mock BaseModel for testing abstract class implementation."""
    mock_model = MagicMock()
    mock_model.fit.return_value = mock_model
    mock_model.predict.return_value = [DOCUMENT_TYPES[0], DOCUMENT_TYPES[1], DOCUMENT_TYPES[2]]
    mock_model.predict_proba.return_value = np.array([
        [0.8, 0.1, 0.05, 0.02, 0.01, 0.01, 0.005, 0.005],
        [0.1, 0.75, 0.05, 0.05, 0.02, 0.01, 0.01, 0.01],
        [0.05, 0.05, 0.8, 0.03, 0.02, 0.02, 0.02, 0.01]
    ])
    mock_model.evaluate.return_value = {
        'accuracy': 0.95,
        'precision': 0.94,
        'recall': 0.93,
        'f1': 0.935
    }
    return mock_model


@pytest.fixture
def generate_test_document():
    """Factory fixture to generate test documents with specific types."""
    def _generate(doc_type: str = None, page_count: int = None, file_size: int = None,
                 content: str = None, mime_type: str = None, quality: str = 'high') -> Dict[str, Any]:
        """Generate a test document with the specified parameters.
        
        Args:
            doc_type: The document type (defaults to random selection)
            page_count: Number of pages (defaults to random 1-10)
            file_size: File size in bytes (defaults to random 100KB-5MB)
            content: Custom content text (defaults to sample content for the doc_type)
            mime_type: MIME type of the document (defaults to random PDF or JPEG)
            quality: Document quality ('high', 'medium', 'low')
            
        Returns:
            A dictionary representing a document
        """
        if doc_type is None:
            doc_type = np.random.choice(DOCUMENT_TYPES)
            
        if page_count is None:
            page_count = np.random.randint(1, 10)
            
        if file_size is None:
            file_size = np.random.randint(100000, 5000000)
            
        if mime_type is None:
            mime_type = 'application/pdf' if np.random.random() > 0.3 else 'image/jpeg'
            
        if content is None:
            content = SAMPLE_DOCUMENT_CONTENT[doc_type]
            
        # Add noise to content based on quality
        if quality == 'medium':
            words = content.split()
            # Replace ~10% of words with 'xxx'
            for i in range(len(words)):
                if np.random.random() < 0.1:
                    words[i] = 'xxx'
            content = ' '.join(words)
        elif quality == 'low':
            words = content.split()
            # Replace ~30% of words with 'xxx'
            for i in range(len(words)):
                if np.random.random() < 0.3:
                    words[i] = 'xxx'
            content = ' '.join(words)
            
        return {
            'id': f'doc_{np.random.randint(1000, 9999)}',
            'content': content,
            'type': doc_type,
            'metadata': {
                'page_count': page_count,
                'file_size': file_size,
                'created_at': pd.Timestamp.now().isoformat(),
                'mime_type': mime_type,
                'quality': quality,
                'ocr_confidence': 0.95 if quality == 'high' else (0.75 if quality == 'medium' else 0.5)
            }
        }
    
    return _generate


@pytest.fixture
def generate_document_batch():
    """Factory fixture to generate batches of test documents."""
    def _generate_batch(n_documents: int = 10, doc_types: List[str] = None) -> List[Dict[str, Any]]:
        """Generate a batch of test documents.
        
        Args:
            n_documents: Number of documents to generate
            doc_types: List of document types to include (defaults to all types)
            
        Returns:
            List of document dictionaries
        """
        if doc_types is None:
            doc_types = DOCUMENT_TYPES
            
        documents = []
        for i in range(n_documents):
            doc_type = np.random.choice(doc_types)
            documents.append({
                'id': f'doc_{i}',
                'content': SAMPLE_DOCUMENT_CONTENT[doc_type],
                'type': doc_type,
                'metadata': {
                    'page_count': np.random.randint(1, 10),
                    'file_size': np.random.randint(100000, 5000000),
                    'created_at': pd.Timestamp.now().isoformat(),
                    'mime_type': 'application/pdf' if np.random.random() > 0.3 else 'image/jpeg',
                    'quality': np.random.choice(['high', 'medium', 'low'], p=[0.7, 0.2, 0.1]),
                    'ocr_confidence': np.random.uniform(0.5, 0.99)
                }
            })
        return documents
    
    return _generate_batch


@pytest.fixture
def feature_vector_generator():
    """Factory fixture to generate feature vectors for testing."""
    def _generate(n_features: int = 100, n_samples: int = 10) -> np.ndarray:
        """Generate random feature vectors for testing.
        
        Args:
            n_features: Number of features in each vector
            n_samples: Number of samples to generate
            
        Returns:
            A numpy array of shape (n_samples, n_features)
        """
        return np.random.random((n_samples, n_features))
    
    return _generate


@pytest.fixture
def confidence_score_calculator():
    """Factory fixture to calculate confidence scores from probability distributions."""
    def _calculate(probabilities: np.ndarray) -> float:
        """Calculate confidence score from class probabilities.
        
        The confidence score is the difference between the highest probability
        and the second highest probability, normalized to [0, 1].
        
        Args:
            probabilities: Array of class probabilities
            
        Returns:
            Confidence score between 0 and 1
        """
        sorted_probs = np.sort(probabilities)[::-1]
        return float(sorted_probs[0] - sorted_probs[1])
    
    return _calculate


@pytest.fixture
def model_evaluation_runner():
    """Factory fixture to run model evaluation with various metrics."""
    def _evaluate(model, X_test, y_test, metrics=None, return_predictions=False) -> Dict[str, Any]:
        """Evaluate a model using specified metrics.
        
        Args:
            model: Trained classifier model
            X_test: Test feature matrix
            y_test: True labels
            metrics: Dictionary of metric functions (defaults to accuracy, precision, recall, f1)
            return_predictions: Whether to include predictions in the results
            
        Returns:
            Dictionary of metric names and scores, and optionally predictions
        """
        if metrics is None:
            metrics = {
                'accuracy': accuracy_score,
                'precision': lambda y_true, y_pred: precision_score(y_true, y_pred, average='weighted'),
                'recall': lambda y_true, y_pred: recall_score(y_true, y_pred, average='weighted'),
                'f1': lambda y_true, y_pred: f1_score(y_true, y_pred, average='weighted')
            }
            
        y_pred = model.predict(X_test)
        results = {name: metric(y_test, y_pred) for name, metric in metrics.items()}
        
        if return_predictions:
            results['predictions'] = y_pred
            if hasattr(model, 'predict_proba'):
                results['probabilities'] = model.predict_proba(X_test)
                
        return results
    
    return _evaluate


@pytest.fixture
def ensemble_evaluator():
    """Factory fixture to evaluate ensemble models combining SVM and Random Forest."""
    def _evaluate_ensemble(svm_model, rf_model, X_test, y_test, weights=(0.5, 0.5)) -> Dict[str, Any]:
        """Evaluate an ensemble of SVM and Random Forest models.
        
        Args:
            svm_model: Trained SVM classifier
            rf_model: Trained Random Forest classifier
            X_test: Test feature matrix
            y_test: True labels
            weights: Tuple of (svm_weight, rf_weight) for weighted voting
            
        Returns:
            Dictionary with evaluation results and ensemble predictions
        """
        # Get probabilities from both models
        svm_proba = svm_model.predict_proba(X_test)
        rf_proba = rf_model.predict_proba(X_test)
        
        # Weighted average of probabilities
        ensemble_proba = weights[0] * svm_proba + weights[1] * rf_proba
        
        # Get class predictions from ensemble probabilities
        ensemble_pred = np.argmax(ensemble_proba, axis=1)
        
        # Convert numeric predictions to class labels
        classes = svm_model.classes_
        ensemble_pred_labels = [classes[idx] for idx in ensemble_pred]
        
        # Calculate metrics
        results = {
            'accuracy': accuracy_score(y_test, ensemble_pred_labels),
            'precision': precision_score(y_test, ensemble_pred_labels, average='weighted'),
            'recall': recall_score(y_test, ensemble_pred_labels, average='weighted'),
            'f1': f1_score(y_test, ensemble_pred_labels, average='weighted'),
            'predictions': ensemble_pred_labels,
            'probabilities': ensemble_proba
        }
        
        return results
    
    return _evaluate_ensemble


@pytest.fixture
def temp_model_path(tmp_path) -> str:
    """Create a temporary directory for model serialization testing."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    return str(models_dir)


@pytest.fixture
def model_serializer():
    """Factory fixture to serialize and deserialize models."""
    def _serialize_model(model, path, filename, use_joblib=True, metadata=None):
        """Serialize a model to disk with optional metadata.
        
        Args:
            model: The model to serialize
            path: Directory path to save the model
            filename: Base filename for the model
            use_joblib: Whether to use joblib (True) or pickle (False)
            metadata: Optional dictionary of metadata to save with the model
            
        Returns:
            Full path to the saved model file
        """
        os.makedirs(path, exist_ok=True)
        model_path = os.path.join(path, f"{filename}.{'joblib' if use_joblib else 'pkl'}")
        
        if use_joblib:
            joblib.dump(model, model_path)
        else:
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
        
        # Save metadata if provided
        if metadata:
            metadata_path = os.path.join(path, f"{filename}_metadata.json")
            with open(metadata_path, 'w') as f:
                import json
                json.dump(metadata, f)
        
        return model_path
    
    return _serialize_model


@pytest.fixture
def model_deserializer():
    """Factory fixture to deserialize models."""
    def _deserialize_model(model_path, use_joblib=True):
        """Deserialize a model from disk.
        
        Args:
            model_path: Path to the serialized model file
            use_joblib: Whether the model was serialized with joblib (True) or pickle (False)
            
        Returns:
            The deserialized model
        """
        if use_joblib:
            return joblib.load(model_path)
        else:
            with open(model_path, 'rb') as f:
                return pickle.load(f)
    
    return _deserialize_model


@pytest.fixture
def model_version_generator():
    """Factory fixture to generate model version information."""
    def _generate_version_info(major=1, minor=0, patch=0, metadata=None):
        """Generate model version information.
        
        Args:
            major: Major version number
            minor: Minor version number
            patch: Patch version number
            metadata: Additional metadata dictionary
            
        Returns:
            Dictionary with version information
        """
        version_info = {
            'version': f"{major}.{minor}.{patch}",
            'timestamp': pd.Timestamp.now().isoformat(),
            'major': major,
            'minor': minor,
            'patch': patch
        }
        
        if metadata:
            version_info.update(metadata)
            
        return version_info
    
    return _generate_version_info


@pytest.fixture
def mock_model_registry() -> MagicMock:
    """Create a mock model registry for testing model versioning and deployment."""
    mock_registry = MagicMock()
    
    # Mock registry data
    registry_data = {
        'svm_classifier': [
            {
                'version': '1.0.0',
                'path': '/models/svm_classifier_1.0.0.joblib',
                'timestamp': '2023-01-01T00:00:00',
                'accuracy': 0.92,
                'active': False
            },
            {
                'version': '1.1.0',
                'path': '/models/svm_classifier_1.1.0.joblib',
                'timestamp': '2023-02-01T00:00:00',
                'accuracy': 0.94,
                'active': True
            }
        ],
        'random_forest_classifier': [
            {
                'version': '1.0.0',
                'path': '/models/rf_classifier_1.0.0.joblib',
                'timestamp': '2023-01-01T00:00:00',
                'accuracy': 0.93,
                'active': False
            },
            {
                'version': '1.1.0',
                'path': '/models/rf_classifier_1.1.0.joblib',
                'timestamp': '2023-02-01T00:00:00',
                'accuracy': 0.95,
                'active': True
            }
        ]
    }
    
    # Mock methods
    mock_registry.get_models.return_value = list(registry_data.keys())
    mock_registry.get_model_versions.side_effect = lambda model_name: registry_data.get(model_name, [])
    mock_registry.get_active_model.side_effect = lambda model_name: next(
        (v for v in registry_data.get(model_name, []) if v.get('active')), None
    )
    mock_registry.register_model.side_effect = lambda model_name, version, path, metadata: True
    mock_registry.activate_model.side_effect = lambda model_name, version: True
    
    return mock_registry


@pytest.fixture
def hyperparameter_grid():
    """Return hyperparameter grids for model optimization."""
    return {
        'svm': {
            'C': [0.1, 1.0, 10.0],
            'kernel': ['linear', 'rbf'],
            'gamma': ['scale', 'auto', 0.1, 0.01],
            'class_weight': [None, 'balanced']
        },
        'random_forest': {
            'n_estimators': [50, 100, 200],
            'max_depth': [None, 10, 20, 30],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'bootstrap': [True, False],
            'class_weight': [None, 'balanced', 'balanced_subsample']
        }
    }


@pytest.fixture
def mock_document_service_config() -> Dict[str, Any]:
    """Return a mock configuration for the document service."""
    return {
        'models': {
            'svm': {
                'enabled': True,
                'weight': 0.5,
                'params': {
                    'C': 1.0,
                    'kernel': 'linear',
                    'gamma': 'scale',
                    'probability': True,
                    'class_weight': 'balanced',
                    'random_state': 42
                }
            },
            'random_forest': {
                'enabled': True,
                'weight': 0.5,
                'params': {
                    'n_estimators': 100,
                    'max_depth': 20,
                    'min_samples_split': 2,
                    'min_samples_leaf': 1,
                    'bootstrap': True,
                    'oob_score': True,
                    'class_weight': 'balanced',
                    'random_state': 42
                }
            }
        },
        'feature_extraction': {
            'tfidf': {
                'enabled': True,
                'max_features': 100,
                'ngram_range': [1, 2],
                'min_df': 2,
                'max_df': 0.9,
                'stop_words': 'english'
            },
            'metadata': {
                'enabled': True,
                'features': ['page_count', 'file_size', 'mime_type']
            },
            'dimensionality_reduction': {
                'enabled': True,
                'method': 'truncated_svd',
                'n_components': 50
            }
        },
        'classification': {
            'confidence_threshold': 0.7,
            'min_probability': 0.5,
            'ensemble_method': 'weighted_average'
        },
        'paths': {
            'models_dir': '/models',
            'temp_dir': '/tmp'
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    }


@pytest.fixture
def mock_classification_result() -> Dict[str, Any]:
    """Return a mock classification result for testing."""
    return {
        'document_id': 'doc_1234',
        'document_type': 'application_form',
        'category': 'application',
        'confidence': 0.92,
        'probabilities': {
            'application_form': 0.92,
            'bank_statement': 0.03,
            'tax_return': 0.01,
            'identity_document': 0.01,
            'business_license': 0.01,
            'invoice': 0.01,
            'utility_bill': 0.005,
            'credit_report': 0.005
        },
        'processing_time': 0.125,  # seconds
        'feature_importance': {
            'merchant cash advance': 0.25,
            'application': 0.20,
            'business name': 0.15,
            'amount requested': 0.10,
            'tax id': 0.08,
            'page_count': 0.05,
            'file_size': 0.03
        },
        'metadata': {
            'model_version': '1.1.0',
            'feature_count': 100,
            'ensemble_weights': {'svm': 0.5, 'random_forest': 0.5},
            'timestamp': pd.Timestamp.now().isoformat()
        },
        'routing': {
            'next_service': 'ocr_service',
            'priority': 'high',
            'queue': 'document-processing'
        }
    }


@pytest.fixture
def mock_feature_importance() -> Dict[str, float]:
    """Return mock feature importance scores for model interpretation."""
    return {
        'merchant cash advance': 0.25,
        'application': 0.20,
        'business name': 0.15,
        'amount requested': 0.10,
        'tax id': 0.08,
        'owner': 0.07,
        'business address': 0.06,
        'page_count': 0.05,
        'file_size': 0.03,
        'years in business': 0.01
    }