# -*- coding: utf-8 -*-
"""Unit tests for the TensorFlow configuration module.

This module contains tests for the OCR Service's tensorflow_config.py module.
Tests verify that TensorFlow configuration correctly sets up model architectures,
hyperparameters, GPU acceleration settings, confidence thresholds, and model paths.
Ensures that OCR processing works correctly with proper model configuration.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
import tensorflow as tf
import sys

# Add the src directory to the path so we can import the config module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from config import tensorflow_config


class TestGPUConfig:
    """Tests for GPU configuration settings."""

    def test_gpu_config_defaults(self):
        """Test that GPU configuration has the expected default values."""
        # Verify GPU acceleration is enabled by default
        assert tensorflow_config.GPU_CONFIG["enable_gpu"] is True
        # Verify memory growth is enabled by default
        assert tensorflow_config.GPU_CONFIG["allow_memory_growth"] is True
        # Verify minimum VRAM requirement is set
        assert tensorflow_config.GPU_CONFIG["min_vram_gb"] == 8
        # Verify mixed precision is enabled for performance
        assert tensorflow_config.GPU_CONFIG["mixed_precision"] is True
        # Verify XLA compilation is enabled for performance
        assert tensorflow_config.GPU_CONFIG["enable_xla"] is True
        # Verify GPU memory fraction is set to a reasonable value
        assert tensorflow_config.GPU_CONFIG["per_process_gpu_memory_fraction"] == 0.9

    def test_gpu_config_memory_settings(self):
        """Test GPU memory configuration settings."""
        # Memory limit should be None by default (use all available memory)
        assert tensorflow_config.GPU_CONFIG["memory_limit_mb"] is None
        # Visible devices should be None by default (use all available GPUs)
        assert tensorflow_config.GPU_CONFIG["visible_devices"] is None


class TestModelPaths:
    """Tests for model paths configuration."""

    def test_model_paths_base_dir(self):
        """Test that the base directory for models is correctly configured."""
        # Test with default environment variable
        assert tensorflow_config.MODEL_PATHS["base_dir"] == "/opt/ocr-service/models"

    @patch.dict(os.environ, {"OCR_MODELS_DIR": "/custom/models/path"})
    def test_model_paths_base_dir_from_env(self):
        """Test that the base directory can be overridden with an environment variable."""
        # Reload the module to pick up the environment variable
        import importlib
        importlib.reload(tensorflow_config)
        assert tensorflow_config.MODEL_PATHS["base_dir"] == "/custom/models/path"

    def test_model_paths_structure(self):
        """Test that all required model paths are defined."""
        # Check that all required model types are defined
        required_models = ["typed_text", "handwritten_text", "hybrid_recognition", "structure_recognition"]
        for model_type in required_models:
            assert model_type in tensorflow_config.MODEL_PATHS
            # Check that each model has the required attributes
            model_config = tensorflow_config.MODEL_PATHS[model_type]
            assert "path" in model_config
            assert "weights" in model_config
            assert "config" in model_config
            assert "labels" in model_config

    def test_model_versioning(self):
        """Test that models are properly versioned."""
        # Check that model paths include version information
        for model_type in ["typed_text", "handwritten_text", "hybrid_recognition", "structure_recognition"]:
            model_path = tensorflow_config.MODEL_PATHS[model_type]["path"]
            # Version should be in the format vX.Y.Z
            assert "/v" in model_path
            # Extract version and verify it follows semantic versioning
            version = model_path.split("/")[-1]
            assert version.startswith("v")
            version_parts = version[1:].split(".")
            assert len(version_parts) == 3
            for part in version_parts:
                assert part.isdigit()


class TestModelHyperparameters:
    """Tests for model hyperparameters configuration."""

    def test_hyperparameters_for_all_models(self):
        """Test that hyperparameters are defined for all models."""
        required_models = ["typed_text", "handwritten_text", "hybrid_recognition", "structure_recognition"]
        for model_type in required_models:
            assert model_type in tensorflow_config.MODEL_HYPERPARAMS

    def test_typed_text_hyperparameters(self):
        """Test that typed text model hyperparameters are correctly configured."""
        hyperparams = tensorflow_config.MODEL_HYPERPARAMS["typed_text"]
        # Check input shape
        assert hyperparams["input_shape"] == (128, 1024, 1)
        # Check batch size
        assert hyperparams["batch_size"] == 32
        # Check learning rate
        assert hyperparams["learning_rate"] == 0.001
        # Check optimizer
        assert hyperparams["optimizer"] == "adam"
        # Check activation
        assert hyperparams["activation"] == "relu"
        # Check dropout rate
        assert hyperparams["dropout_rate"] == 0.2
        # Check L2 regularization
        assert hyperparams["l2_regularization"] == 0.0001
        # Check batch normalization
        assert hyperparams["use_batch_norm"] is True

    def test_handwritten_text_hyperparameters(self):
        """Test that handwritten text model hyperparameters are correctly configured."""
        hyperparams = tensorflow_config.MODEL_HYPERPARAMS["handwritten_text"]
        # Check input shape
        assert hyperparams["input_shape"] == (64, 800, 1)
        # Check batch size
        assert hyperparams["batch_size"] == 16
        # Check learning rate
        assert hyperparams["learning_rate"] == 0.0005
        # Check optimizer
        assert hyperparams["optimizer"] == "adam"
        # Check activation
        assert hyperparams["activation"] == "relu"
        # Check dropout rate
        assert hyperparams["dropout_rate"] == 0.3
        # Check L2 regularization
        assert hyperparams["l2_regularization"] == 0.0002
        # Check batch normalization
        assert hyperparams["use_batch_norm"] is True
        # Check bidirectional LSTM
        assert hyperparams["bidirectional_lstm"] is True
        # Check LSTM units
        assert hyperparams["lstm_units"] == 256

    def test_hybrid_recognition_hyperparameters(self):
        """Test that hybrid recognition model hyperparameters are correctly configured."""
        hyperparams = tensorflow_config.MODEL_HYPERPARAMS["hybrid_recognition"]
        # Check input shape
        assert hyperparams["input_shape"] == (96, 1024, 1)
        # Check batch size
        assert hyperparams["batch_size"] == 24
        # Check learning rate
        assert hyperparams["learning_rate"] == 0.0008
        # Check optimizer
        assert hyperparams["optimizer"] == "adam"
        # Check activation
        assert hyperparams["activation"] == "relu"
        # Check dropout rate
        assert hyperparams["dropout_rate"] == 0.25
        # Check L2 regularization
        assert hyperparams["l2_regularization"] == 0.00015
        # Check batch normalization
        assert hyperparams["use_batch_norm"] is True
        # Check bidirectional LSTM
        assert hyperparams["bidirectional_lstm"] is True
        # Check LSTM units
        assert hyperparams["lstm_units"] == 192

    def test_structure_recognition_hyperparameters(self):
        """Test that structure recognition model hyperparameters are correctly configured."""
        hyperparams = tensorflow_config.MODEL_HYPERPARAMS["structure_recognition"]
        # Check input shape
        assert hyperparams["input_shape"] == (1024, 1024, 3)
        # Check batch size
        assert hyperparams["batch_size"] == 8
        # Check learning rate
        assert hyperparams["learning_rate"] == 0.0003
        # Check optimizer
        assert hyperparams["optimizer"] == "adam"
        # Check backbone
        assert hyperparams["backbone"] == "resnet50"
        # Check feature pyramid levels
        assert hyperparams["feature_pyramid_levels"] == [3, 4, 5, 6, 7]
        # Check anchor scales
        assert hyperparams["anchor_scales"] == [32, 64, 128, 256, 512]
        # Check anchor ratios
        assert hyperparams["anchor_ratios"] == [0.5, 1, 2]
        # Check RPN NMS threshold
        assert hyperparams["rpn_nms_threshold"] == 0.7
        # Check detection NMS threshold
        assert hyperparams["detection_nms_threshold"] == 0.3
        # Check detection minimum confidence
        assert hyperparams["detection_min_confidence"] == 0.7


class TestConfidenceThresholds:
    """Tests for confidence thresholds configuration."""

    def test_global_min_confidence(self):
        """Test that the global minimum confidence threshold is correctly configured."""
        assert tensorflow_config.CONFIDENCE_THRESHOLDS["global_min_confidence"] == 0.75

    def test_field_specific_thresholds(self):
        """Test that field-specific confidence thresholds are correctly configured."""
        fields = tensorflow_config.CONFIDENCE_THRESHOLDS["fields"]
        # Check critical fields have higher thresholds
        assert fields["ein"] == 0.95
        assert fields["bank_account"] == 0.98
        assert fields["routing_number"] == 0.98
        assert fields["owner_ssn"] == 0.98
        # Check default threshold
        assert fields["default"] == 0.80

    def test_document_type_thresholds(self):
        """Test that document type confidence thresholds are correctly configured."""
        doc_types = tensorflow_config.CONFIDENCE_THRESHOLDS["document_types"]
        # Check that ID documents have higher threshold
        assert doc_types["id_document"] == 0.95
        # Check that tax returns have higher threshold
        assert doc_types["tax_return"] == 0.90
        # Check default threshold
        assert doc_types["default"] == 0.80

    def test_get_confidence_threshold(self):
        """Test the get_confidence_threshold function."""
        # Test with field only
        assert tensorflow_config.get_confidence_threshold("legal_name") == 0.85
        # Test with field and document type
        assert tensorflow_config.get_confidence_threshold("legal_name", "application_form") == 0.85
        # Test with field and document type where document threshold is higher
        assert tensorflow_config.get_confidence_threshold("legal_name", "tax_return") == 0.90
        # Test with field that has very high threshold and document type
        assert tensorflow_config.get_confidence_threshold("ein", "application_form") == 0.95
        # Test with unknown field (should use default)
        assert tensorflow_config.get_confidence_threshold("unknown_field") == 0.80
        # Test with unknown field and document type
        assert tensorflow_config.get_confidence_threshold("unknown_field", "tax_return") == 0.90
        # Test with unknown field and unknown document type
        assert tensorflow_config.get_confidence_threshold("unknown_field", "unknown_doc") == 0.80


class TestModelArchitectures:
    """Tests for model architecture configurations."""

    def test_typed_text_architecture(self):
        """Test that typed text model architecture is correctly configured."""
        arch = tensorflow_config.MODEL_ARCHITECTURES["typed_text"]
        # Check architecture type
        assert arch["type"] == "cnn_lstm_ctc"
        # Check CNN layers
        assert arch["cnn_layers"] == 5
        # Check CNN filters
        assert arch["cnn_filters"] == [64, 128, 256, 256, 512]
        # Check CNN kernel sizes
        assert arch["cnn_kernel_sizes"] == [(3, 3), (3, 3), (3, 3), (3, 3), (3, 3)]
        # Check CNN pool sizes
        assert arch["cnn_pool_sizes"] == [(2, 2), (2, 2), (2, 1), (2, 1), (2, 1)]
        # Check LSTM layers
        assert arch["lstm_layers"] == 2
        # Check LSTM units
        assert arch["lstm_units"] == 256
        # Check bidirectional
        assert arch["bidirectional"] is True

    def test_handwritten_text_architecture(self):
        """Test that handwritten text model architecture is correctly configured."""
        arch = tensorflow_config.MODEL_ARCHITECTURES["handwritten_text"]
        # Check architecture type
        assert arch["type"] == "cnn_lstm_attention"
        # Check CNN layers
        assert arch["cnn_layers"] == 6
        # Check CNN filters
        assert arch["cnn_filters"] == [64, 128, 256, 256, 512, 512]
        # Check CNN kernel sizes
        assert arch["cnn_kernel_sizes"] == [(3, 3), (3, 3), (3, 3), (3, 3), (3, 3), (3, 3)]
        # Check CNN pool sizes
        assert arch["cnn_pool_sizes"] == [(2, 2), (2, 2), (2, 1), (2, 1), (2, 1), (1, 1)]
        # Check LSTM layers
        assert arch["lstm_layers"] == 3
        # Check LSTM units
        assert arch["lstm_units"] == 256
        # Check attention dimension
        assert arch["attention_dim"] == 128
        # Check bidirectional
        assert arch["bidirectional"] is True

    def test_hybrid_recognition_architecture(self):
        """Test that hybrid recognition model architecture is correctly configured."""
        arch = tensorflow_config.MODEL_ARCHITECTURES["hybrid_recognition"]
        # Check architecture type
        assert arch["type"] == "cnn_transformer"
        # Check CNN layers
        assert arch["cnn_layers"] == 5
        # Check CNN filters
        assert arch["cnn_filters"] == [64, 128, 256, 256, 512]
        # Check CNN kernel sizes
        assert arch["cnn_kernel_sizes"] == [(3, 3), (3, 3), (3, 3), (3, 3), (3, 3)]
        # Check CNN pool sizes
        assert arch["cnn_pool_sizes"] == [(2, 2), (2, 2), (2, 1), (2, 1), (2, 1)]
        # Check transformer layers
        assert arch["transformer_layers"] == 4
        # Check transformer heads
        assert arch["transformer_heads"] == 8
        # Check transformer dimension
        assert arch["transformer_dim"] == 512
        # Check transformer feed-forward dimension
        assert arch["transformer_ff_dim"] == 2048

    def test_structure_recognition_architecture(self):
        """Test that structure recognition model architecture is correctly configured."""
        arch = tensorflow_config.MODEL_ARCHITECTURES["structure_recognition"]
        # Check architecture type
        assert arch["type"] == "mask_rcnn"
        # Check backbone
        assert arch["backbone"] == "resnet50"
        # Check FPN layers
        assert arch["fpn_layers"] == ["P2", "P3", "P4", "P5", "P6"]
        # Check ROI pool size
        assert arch["roi_pool_size"] == (7, 7)
        # Check mask pool size
        assert arch["mask_pool_size"] == (14, 14)
        # Check mask shape
        assert arch["mask_shape"] == (28, 28)
        # Check RPN anchor scales
        assert arch["rpn_anchor_scales"] == (32, 64, 128, 256, 512)
        # Check RPN anchor ratios
        assert arch["rpn_anchor_ratios"] == [0.5, 1, 2]
        # Check RPN NMS threshold
        assert arch["rpn_nms_threshold"] == 0.7
        # Check RPN train anchors per image
        assert arch["rpn_train_anchors_per_image"] == 256
        # Check post NMS ROIs for training
        assert arch["post_nms_rois_training"] == 2000
        # Check post NMS ROIs for inference
        assert arch["post_nms_rois_inference"] == 1000
        # Check mini mask usage
        assert arch["use_mini_mask"] is True
        # Check mini mask shape
        assert arch["mini_mask_shape"] == (56, 56)


class TestTFOptimization:
    """Tests for TensorFlow optimization settings."""

    def test_optimization_settings(self):
        """Test that TensorFlow optimization settings are correctly configured."""
        # Check XLA compilation
        assert tensorflow_config.TF_OPTIMIZATION["enable_xla"] is True
        # Check mixed precision
        assert tensorflow_config.TF_OPTIMIZATION["mixed_precision"] is True
        # Check inter-op parallelism threads
        assert tensorflow_config.TF_OPTIMIZATION["inter_op_parallelism_threads"] == 0
        # Check intra-op parallelism threads
        assert tensorflow_config.TF_OPTIMIZATION["intra_op_parallelism_threads"] == 0
        # Check tensor fusion
        assert tensorflow_config.TF_OPTIMIZATION["enable_tensor_fusion"] is True
        # Check tensor fusion threshold
        assert tensorflow_config.TF_OPTIMIZATION["tensor_fusion_threshold"] == 64
        # Check JIT level
        assert tensorflow_config.TF_OPTIMIZATION["jit_level"] == 1
        # Check optimization level
        assert tensorflow_config.TF_OPTIMIZATION["optimization_level"] == 3


class TestSessionConfig:
    """Tests for TensorFlow session configuration."""

    def test_get_session_config(self):
        """Test that get_session_config returns the expected configuration."""
        config = tensorflow_config.get_session_config()
        # Check allow soft placement
        assert config["allow_soft_placement"] is True
        # Check log device placement
        assert config["log_device_placement"] is False
        # Check GPU options
        assert "gpu_options" in config
        assert config["gpu_options"]["allow_growth"] is True
        assert config["gpu_options"]["per_process_gpu_memory_fraction"] is None
        # Check device count (should be None when GPU is enabled)
        assert config["device_count"] is None
        # Check inter-op parallelism threads
        assert config["inter_op_parallelism_threads"] == 0
        # Check intra-op parallelism threads
        assert config["intra_op_parallelism_threads"] == 0
        # Check use per session threads
        assert config["use_per_session_threads"] is True
        # Check graph options
        assert "graph_options" in config
        assert "optimizer_options" in config["graph_options"]
        assert config["graph_options"]["optimizer_options"]["global_jit_level"] == 1
        assert config["graph_options"]["optimizer_options"]["opt_level"] == 3

    @patch.dict(tensorflow_config.GPU_CONFIG, {"enable_gpu": False})
    def test_get_session_config_no_gpu(self):
        """Test that get_session_config handles disabled GPU correctly."""
        config = tensorflow_config.get_session_config()
        # Check device count (should disable GPU)
        assert config["device_count"] == {"GPU": 0}

    @patch.dict(tensorflow_config.GPU_CONFIG, {"allow_memory_growth": False, "per_process_gpu_memory_fraction": 0.5})
    def test_get_session_config_memory_fraction(self):
        """Test that get_session_config handles memory fraction correctly."""
        config = tensorflow_config.get_session_config()
        # Check GPU options
        assert config["gpu_options"]["allow_growth"] is False
        assert config["gpu_options"]["per_process_gpu_memory_fraction"] == 0.5


class TestGetModelConfig:
    """Tests for the get_model_config function."""

    def test_get_model_config_valid_type(self):
        """Test that get_model_config returns the expected configuration for valid model types."""
        model_types = ["typed_text", "handwritten_text", "hybrid_recognition", "structure_recognition"]
        for model_type in model_types:
            config = tensorflow_config.get_model_config(model_type)
            # Check that the config has the expected sections
            assert "paths" in config
            assert "hyperparameters" in config
            assert "architecture" in config
            # Check that paths are correctly constructed
            base_dir = tensorflow_config.MODEL_PATHS["base_dir"]
            model_path = tensorflow_config.MODEL_PATHS[model_type]["path"]
            assert config["paths"]["model_dir"] == os.path.join(base_dir, model_path)
            # Check that hyperparameters match the expected values
            assert config["hyperparameters"] == tensorflow_config.MODEL_HYPERPARAMS[model_type]
            # Check that architecture matches the expected values
            assert config["architecture"] == tensorflow_config.MODEL_ARCHITECTURES[model_type]

    def test_get_model_config_invalid_type(self):
        """Test that get_model_config raises ValueError for invalid model types."""
        with pytest.raises(ValueError):
            tensorflow_config.get_model_config("invalid_model_type")


class TestInitializeTensorflow:
    """Tests for the initialize_tensorflow function."""

    @patch("tensorflow.config.experimental.list_physical_devices")
    @patch("tensorflow.config.experimental.set_memory_growth")
    @patch("tensorflow.python.client.device_lib.list_local_devices")
    @patch("tensorflow.keras.mixed_precision.Policy")
    @patch("tensorflow.keras.mixed_precision.set_global_policy")
    @patch("tensorflow.config.optimizer.set_jit")
    def test_initialize_tensorflow_with_gpus(self, mock_set_jit, mock_set_global_policy, mock_policy,
                                           mock_list_local_devices, mock_set_memory_growth, mock_list_physical_devices):
        """Test that initialize_tensorflow correctly configures TensorFlow with GPUs."""
        # Mock GPU devices
        mock_gpu = MagicMock()
        mock_gpu.name = "GPU:0"
        mock_list_physical_devices.return_value = [mock_gpu]

        # Mock device lib
        mock_device = MagicMock()
        mock_device.device_type = "GPU"
        mock_device.name = "GPU:0"
        mock_device.memory_limit = 10 * 1024 * 1024 * 1024  # 10 GB
        mock_list_local_devices.return_value = [mock_device]

        # Mock policy
        mock_policy.return_value = "mixed_float16"

        # Call the function
        tensorflow_config.initialize_tensorflow()

        # Check that GPUs were detected
        mock_list_physical_devices.assert_called_once_with('GPU')

        # Check that memory growth was enabled
        mock_set_memory_growth.assert_called_once_with(mock_gpu, True)

        # Check that mixed precision was enabled
        mock_policy.assert_called_once_with('mixed_float16')
        mock_set_global_policy.assert_called_once()

        # Check that XLA compilation was enabled
        mock_set_jit.assert_called_once_with(True)

    @patch("tensorflow.config.experimental.list_physical_devices")
    @patch("tensorflow.python.client.device_lib.list_local_devices")
    @patch("tensorflow.keras.mixed_precision.Policy")
    @patch("tensorflow.keras.mixed_precision.set_global_policy")
    @patch("tensorflow.config.optimizer.set_jit")
    def test_initialize_tensorflow_no_gpus(self, mock_set_jit, mock_set_global_policy, mock_policy,
                                         mock_list_local_devices, mock_list_physical_devices):
        """Test that initialize_tensorflow handles the case where no GPUs are available."""
        # Mock no GPU devices
        mock_list_physical_devices.return_value = []

        # Call the function
        tensorflow_config.initialize_tensorflow()

        # Check that GPUs were checked
        mock_list_physical_devices.assert_called_once_with('GPU')

        # Check that mixed precision was not enabled (no GPUs)
        mock_policy.assert_not_called()
        mock_set_global_policy.assert_not_called()

        # Check that XLA compilation was still enabled
        mock_set_jit.assert_called_once_with(True)

    @patch("tensorflow.config.experimental.list_physical_devices")
    @patch("tensorflow.config.experimental.set_visible_devices")
    @patch("tensorflow.python.client.device_lib.list_local_devices")
    @patch("tensorflow.keras.mixed_precision.Policy")
    @patch("tensorflow.keras.mixed_precision.set_global_policy")
    @patch("tensorflow.config.optimizer.set_jit")
    @patch.dict(tensorflow_config.GPU_CONFIG, {"visible_devices": [0]})
    def test_initialize_tensorflow_visible_devices(self, mock_set_jit, mock_set_global_policy, mock_policy,
                                                 mock_list_local_devices, mock_set_visible_devices, mock_list_physical_devices):
        """Test that initialize_tensorflow correctly configures visible devices."""
        # Mock GPU devices
        mock_gpu = MagicMock()
        mock_gpu.name = "GPU:0"
        mock_list_physical_devices.return_value = [mock_gpu]

        # Mock device lib
        mock_device = MagicMock()
        mock_device.device_type = "GPU"
        mock_device.name = "GPU:0"
        mock_device.memory_limit = 10 * 1024 * 1024 * 1024  # 10 GB
        mock_list_local_devices.return_value = [mock_device]

        # Call the function
        tensorflow_config.initialize_tensorflow()

        # Check that visible devices were set
        mock_set_visible_devices.assert_called_once_with([mock_gpu], 'GPU')

    @patch("tensorflow.config.experimental.list_physical_devices")
    @patch("tensorflow.config.experimental.set_virtual_device_configuration")
    @patch("tensorflow.config.experimental.VirtualDeviceConfiguration")
    @patch("tensorflow.python.client.device_lib.list_local_devices")
    @patch("tensorflow.keras.mixed_precision.Policy")
    @patch("tensorflow.keras.mixed_precision.set_global_policy")
    @patch("tensorflow.config.optimizer.set_jit")
    @patch.dict(tensorflow_config.GPU_CONFIG, {"memory_limit_mb": 4096})
    def test_initialize_tensorflow_memory_limit(self, mock_set_jit, mock_set_global_policy, mock_policy,
                                              mock_list_local_devices, mock_virtual_device_config,
                                              mock_set_virtual_device_config, mock_list_physical_devices):
        """Test that initialize_tensorflow correctly configures memory limits."""
        # Mock GPU devices
        mock_gpu = MagicMock()
        mock_gpu.name = "GPU:0"
        mock_list_physical_devices.return_value = [mock_gpu]

        # Mock device lib
        mock_device = MagicMock()
        mock_device.device_type = "GPU"
        mock_device.name = "GPU:0"
        mock_device.memory_limit = 10 * 1024 * 1024 * 1024  # 10 GB
        mock_list_local_devices.return_value = [mock_device]

        # Mock virtual device configuration
        mock_virtual_config = MagicMock()
        mock_virtual_device_config.return_value = mock_virtual_config

        # Call the function
        tensorflow_config.initialize_tensorflow()

        # Check that memory limit was set
        mock_virtual_device_config.assert_called_once_with(memory_limit=4096)
        mock_set_virtual_device_config.assert_called_once_with(mock_gpu, [mock_virtual_config])

    @patch("tensorflow.config.experimental.list_physical_devices")
    @patch("tensorflow.python.client.device_lib.list_local_devices")
    def test_initialize_tensorflow_insufficient_vram(self, mock_list_local_devices, mock_list_physical_devices):
        """Test that initialize_tensorflow warns when VRAM is insufficient."""
        # Mock GPU devices
        mock_gpu = MagicMock()
        mock_gpu.name = "GPU:0"
        mock_list_physical_devices.return_value = [mock_gpu]

        # Mock device lib with insufficient VRAM
        mock_device = MagicMock()
        mock_device.device_type = "GPU"
        mock_device.name = "GPU:0"
        mock_device.memory_limit = 4 * 1024 * 1024 * 1024  # 4 GB (less than 8 GB required)
        mock_list_local_devices.return_value = [mock_device]

        # Call the function with a logger mock to capture warnings
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            tensorflow_config.initialize_tensorflow()

            # Check that a warning was logged
            mock_logger.warning.assert_any_call(
                "GPU GPU:0 has 4.00GB VRAM, which is less than the required 8GB. This may affect performance."
            )

    @patch("tensorflow.__version__", "2.14.0")
    def test_initialize_tensorflow_version_mismatch(self):
        """Test that initialize_tensorflow warns when TensorFlow version doesn't match."""
        # Call the function with a logger mock to capture warnings
        with patch("logging.getLogger") as mock_get_logger:
            with patch("tensorflow.config.experimental.list_physical_devices", return_value=[]):
                with patch("tensorflow.config.optimizer.set_jit"):
                    mock_logger = MagicMock()
                    mock_get_logger.return_value = mock_logger
                    tensorflow_config.initialize_tensorflow()

                    # Check that a warning was logged
                    mock_logger.warning.assert_any_call(
                        "TensorFlow version mismatch. Required: 2.15.0, Found: 2.14.0. "
                        "This may cause compatibility issues."
                    )

    def test_initialize_tensorflow_import_error(self):
        """Test that initialize_tensorflow raises ImportError when TensorFlow is not available."""
        # Mock an import error
        with patch.dict(sys.modules, {"tensorflow": None}):
            with pytest.raises(ImportError):
                tensorflow_config.initialize_tensorflow()


if __name__ == "__main__":
    pytest.main()