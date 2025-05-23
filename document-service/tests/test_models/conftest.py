import os
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, MagicMock
from sklearn.datasets import make_classification
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_curve, auc
from sklearn.model_selection import train_test_split, cross_val_score

# Constants for testing
DOCUMENT_TYPES = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
MIN_ACCURACY_THRESHOLD = 0.99  # 99% accuracy requirement


# Document fixtures
@pytest.fixture
def sample_document():
    """Fixture that returns a basic sample document for testing."""
    return {
        'id': 'doc-001',
        'filename': 'sample_invoice.pdf',
        'content': 'This is a sample invoice document for testing purposes.',
        'metadata': {
            'size': 1024,
            'pages': 1,
            'created_at': '2025-05-01T10:00:00Z'
        }
    }


@pytest.fixture
def sample_documents():
    """Fixture that returns a list of sample documents of different types for testing."""
    return [
        {
            'id': 'doc-001',
            'filename': 'sample_invoice.pdf',
            'content': 'This is a sample invoice from ABC Corp for $500.',
            'metadata': {
                'size': 1024,
                'pages': 1,
                'created_at': '2025-05-01T10:00:00Z'
            },
            'type': 'invoice'
        },
        {
            'id': 'doc-002',
            'filename': 'business_license.pdf',
            'content': 'Business License for XYZ LLC valid until 2026.',
            'metadata': {
                'size': 2048,
                'pages': 2,
                'created_at': '2025-05-02T11:00:00Z'
            },
            'type': 'license'
        },
        {
            'id': 'doc-003',
            'filename': 'bank_statement.pdf',
            'content': 'Monthly statement for account #12345 with balance $10,000.',
            'metadata': {
                'size': 3072,
                'pages': 3,
                'created_at': '2025-05-03T12:00:00Z'
            },
            'type': 'bank_statement'
        },
        {
            'id': 'doc-004',
            'filename': 'tax_return.pdf',
            'content': 'Annual tax return for fiscal year 2024.',
            'metadata': {
                'size': 4096,
                'pages': 4,
                'created_at': '2025-05-04T13:00:00Z'
            },
            'type': 'tax_document'
        },
        {
            'id': 'doc-005',
            'filename': 'application_form.pdf',
            'content': 'Application form for merchant cash advance.',
            'metadata': {
                'size': 5120,
                'pages': 5,
                'created_at': '2025-05-05T14:00:00Z'
            },
            'type': 'application'
        }
    ]


@pytest.fixture
def document_dataframe(sample_documents):
    """Fixture that returns a pandas DataFrame of sample documents for testing."""
    return pd.DataFrame(sample_documents)


@pytest.fixture(params=['invoice', 'license', 'bank_statement', 'tax_document', 'application'])
def document_by_type(request, sample_documents):
    """Parameterized fixture that returns a document of a specific type."""
    doc_type = request.param
    for doc in sample_documents:
        if doc['type'] == doc_type:
            return doc
    return None


# Feature extraction fixtures
@pytest.fixture
def tfidf_vectorizer():
    """Fixture that returns a TF-IDF vectorizer for text feature extraction."""
    return TfidfVectorizer(
        max_features=100,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.9
    )


@pytest.fixture
def document_features(sample_documents, tfidf_vectorizer):
    """Fixture that returns TF-IDF features extracted from sample documents."""
    contents = [doc['content'] for doc in sample_documents]
    return tfidf_vectorizer.fit_transform(contents)


@pytest.fixture
def document_features_with_metadata(sample_documents, document_features):
    """Fixture that returns document features combined with metadata features."""
    # Extract metadata features (page count and size)
    metadata_features = np.array([
        [doc['metadata']['pages'], doc['metadata']['size']] 
        for doc in sample_documents
    ])
    
    # Convert sparse matrix to dense for concatenation
    text_features = document_features.toarray()
    
    # Combine text features with metadata features
    # In a real scenario, you might use more sophisticated feature engineering
    combined_features = np.hstack((text_features, metadata_features))
    
    return combined_features


@pytest.fixture
def feature_extraction_mock():
    """Fixture that returns a mock feature extraction function."""
    mock = MagicMock()
    # Configure the mock to return a feature vector of appropriate shape
    mock.return_value = np.random.rand(1, 50)
    return mock


# Classification fixtures
@pytest.fixture
def document_labels(sample_documents):
    """Fixture that returns document type labels for classification testing."""
    return [doc['type'] for doc in sample_documents]


@pytest.fixture
def mock_svm_classifier():
    """Fixture that returns a mock SVM classifier."""
    mock = MagicMock(spec=SVC)
    mock.fit.return_value = mock
    mock.predict.return_value = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    mock.predict_proba.return_value = np.array([
        [0.8, 0.05, 0.05, 0.05, 0.05],
        [0.05, 0.8, 0.05, 0.05, 0.05],
        [0.05, 0.05, 0.8, 0.05, 0.05],
        [0.05, 0.05, 0.05, 0.8, 0.05],
        [0.05, 0.05, 0.05, 0.05, 0.8]
    ])
    return mock


@pytest.fixture
def mock_random_forest_classifier():
    """Fixture that returns a mock Random Forest classifier."""
    mock = MagicMock(spec=RandomForestClassifier)
    mock.fit.return_value = mock
    mock.predict.return_value = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    mock.predict_proba.return_value = np.array([
        [0.75, 0.06, 0.06, 0.06, 0.07],
        [0.06, 0.75, 0.06, 0.07, 0.06],
        [0.06, 0.06, 0.75, 0.06, 0.07],
        [0.06, 0.07, 0.06, 0.75, 0.06],
        [0.07, 0.06, 0.07, 0.06, 0.74]
    ])
    return mock


@pytest.fixture
def trained_svm_classifier(document_features, document_labels):
    """Fixture that returns a trained SVM classifier on sample documents."""
    classifier = SVC(probability=True, kernel='linear', C=1.0)
    classifier.fit(document_features.toarray(), document_labels)
    return classifier


@pytest.fixture
def trained_random_forest_classifier(document_features, document_labels):
    """Fixture that returns a trained Random Forest classifier on sample documents."""
    classifier = RandomForestClassifier(n_estimators=100, random_state=42)
    classifier.fit(document_features.toarray(), document_labels)
    return classifier


# Synthetic data fixtures
@pytest.fixture
def synthetic_classification_data():
    """Fixture that returns synthetic data for classification testing."""
    X, y = make_classification(
        n_samples=100,
        n_features=20,
        n_informative=10,
        n_redundant=5,
        n_classes=5,
        random_state=42
    )
    # Map numeric labels to document types
    label_map = {0: 'invoice', 1: 'license', 2: 'bank_statement', 3: 'tax_document', 4: 'application'}
    y_mapped = [label_map[label] for label in y]
    return X, y_mapped


@pytest.fixture
def train_test_data(synthetic_classification_data):
    """Fixture that returns train-test split data for model evaluation."""
    X, y = synthetic_classification_data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    return X_train, X_test, y_train, y_test


@pytest.fixture
def document_vectors():
    """Fixture that returns document vectors for different document types."""
    # Create feature vectors for different document types with distinctive patterns
    vectors = {
        'invoice': np.array([0.8, 0.1, 0.0, 0.0, 0.1, 0.7, 0.2, 0.0, 0.0, 0.1]),
        'license': np.array([0.1, 0.7, 0.1, 0.0, 0.1, 0.1, 0.8, 0.0, 0.0, 0.1]),
        'bank_statement': np.array([0.0, 0.1, 0.8, 0.1, 0.0, 0.0, 0.1, 0.7, 0.1, 0.1]),
        'tax_document': np.array([0.0, 0.0, 0.1, 0.8, 0.1, 0.0, 0.0, 0.1, 0.7, 0.2]),
        'application': np.array([0.1, 0.1, 0.0, 0.1, 0.7, 0.1, 0.1, 0.1, 0.1, 0.7])
    }
    return vectors


# Evaluation fixtures
@pytest.fixture
def classification_metrics():
    """Fixture that returns a function to calculate classification metrics."""
    def _calculate_metrics(y_true, y_pred, y_prob=None):
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision_macro': precision_score(y_true, y_pred, average='macro'),
            'recall_macro': recall_score(y_true, y_pred, average='macro'),
            'f1_macro': f1_score(y_true, y_pred, average='macro'),
            'confusion_matrix': confusion_matrix(y_true, y_pred)
        }
        
        # Calculate ROC curve and AUC if probability scores are provided
        if y_prob is not None:
            # For multi-class, we calculate one-vs-rest ROC curves
            roc_curves = {}
            aucs = {}
            
            # Get unique classes
            classes = sorted(set(y_true))
            
            for i, cls in enumerate(classes):
                # Convert to binary classification problem
                y_true_binary = [1 if y == cls else 0 for y in y_true]
                
                # Get probability for this class
                if y_prob.ndim > 1 and y_prob.shape[1] > 1:
                    y_score = y_prob[:, i]
                else:
                    # Handle binary classification case
                    y_score = y_prob if i == 1 else 1 - y_prob
                
                # Calculate ROC curve and AUC
                fpr, tpr, thresholds = roc_curve(y_true_binary, y_score)
                roc_auc = auc(fpr, tpr)
                
                roc_curves[cls] = (fpr, tpr, thresholds)
                aucs[cls] = roc_auc
            
            metrics['roc_curves'] = roc_curves
            metrics['auc_scores'] = aucs
            metrics['mean_auc'] = sum(aucs.values()) / len(aucs)
        
        return metrics
    
    return _calculate_metrics


@pytest.fixture
def mock_evaluation_results():
    """Fixture that returns mock evaluation results for testing."""
    return {
        'accuracy': 0.95,
        'precision_macro': 0.94,
        'recall_macro': 0.93,
        'f1_macro': 0.935,
        'confusion_matrix': np.array([
            [19, 1, 0, 0, 0],
            [0, 18, 2, 0, 0],
            [0, 0, 20, 0, 0],
            [0, 0, 0, 19, 1],
            [1, 0, 0, 0, 19]
        ])
    }


# Model serialization fixtures
@pytest.fixture
def temp_model_path(tmp_path):
    """Fixture that returns a temporary path for model serialization testing."""
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    return model_dir


@pytest.fixture
def model_metadata():
    """Fixture that returns sample model metadata for serialization testing."""
    return {
        'model_name': 'document_classifier_v1',
        'model_type': 'svm',
        'created_at': '2025-05-10T15:00:00Z',
        'version': '1.0.0',
        'accuracy': 0.95,
        'f1_score': 0.94,
        'parameters': {
            'kernel': 'linear',
            'C': 1.0,
            'probability': True
        },
        'feature_extraction': {
            'vectorizer': 'tfidf',
            'max_features': 100,
            'ngram_range': [1, 2]
        },
        'classes': ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    }


# Helper functions
@pytest.fixture
def create_test_document():
    """Fixture that returns a function to create test documents with custom attributes."""
    def _create_document(doc_id=None, filename=None, content=None, doc_type=None, pages=1, size=1024):
        return {
            'id': doc_id or f'doc-{np.random.randint(1000, 9999)}',
            'filename': filename or f'document_{np.random.randint(1000, 9999)}.pdf',
            'content': content or f'This is a sample {doc_type or "document"} for testing.',
            'metadata': {
                'size': size,
                'pages': pages,
                'created_at': '2025-05-01T10:00:00Z'
            },
            'type': doc_type or 'unknown'
        }
    return _create_document


@pytest.fixture
def create_test_document_batch():
    """Fixture that returns a function to create a batch of test documents."""
    def _create_document_batch(count=10, doc_types=None):
        if doc_types is None:
            doc_types = DOCUMENT_TYPES
        
        documents = []
        for i in range(count):
            doc_type = doc_types[i % len(doc_types)]
            documents.append({
                'id': f'doc-{1000 + i}',
                'filename': f'{doc_type}_{1000 + i}.pdf',
                'content': f'This is a sample {doc_type} document for testing batch {i}.',
                'metadata': {
                    'size': 1024 * (i % 5 + 1),
                    'pages': i % 10 + 1,
                    'created_at': f'2025-05-{(i % 30) + 1:02d}T10:00:00Z'
                },
                'type': doc_type
            })
        return documents
    return _create_document_batch


@pytest.fixture
def mock_confidence_scores():
    """Fixture that returns mock confidence scores for document classification."""
    def _get_confidence_scores(doc_type=None):
        # Default high confidence for the correct type, low for others
        scores = {
            'invoice': 0.1,
            'license': 0.1,
            'bank_statement': 0.1,
            'tax_document': 0.1,
            'application': 0.1
        }
        
        if doc_type in scores:
            # Set high confidence (0.6) for the specified type
            scores[doc_type] = 0.6
        
        return scores
    return _get_confidence_scores


@pytest.fixture
def cross_validation_fixture():
    """Fixture that performs cross-validation on a classifier with test data."""
    def _cross_validate(classifier, X, y, cv=5):
        cv_scores = cross_val_score(classifier, X, y, cv=cv)
        return {
            'cv_scores': cv_scores,
            'mean_score': np.mean(cv_scores),
            'std_score': np.std(cv_scores),
            'min_score': np.min(cv_scores),
            'max_score': np.max(cv_scores)
        }
    return _cross_validate