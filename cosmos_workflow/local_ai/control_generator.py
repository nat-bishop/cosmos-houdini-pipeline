#!/usr/bin/env python3
"""
Control modality generation module.

Generates control modality videos (depth, segmentation, edge) from input videos
using fast local AI models for Cosmos Transfer workflows.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import torch
import torchvision.transforms as transforms
from PIL import Image
from dataclasses import dataclass
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ControlGenerationConfig:
    """Configuration for control modality generation."""
    extract_every_n_frames: int = 1  # Process every Nth frame for speed
    use_gpu: bool = True  # Use GPU if available
    depth_model: str = "MiDaS"  # Depth estimation model
    segmentation_model: str = "DeepLabV3"  # Segmentation model
    edge_threshold_low: int = 50  # Canny edge detection low threshold
    edge_threshold_high: int = 150  # Canny edge detection high threshold
    single_frame_mode: bool = False  # Process only middle frame for speed


class ControlModalityGenerator:
    """
    Generates control modality videos from input videos.
    
    This class uses lightweight AI models to generate depth, segmentation,
    and edge detection videos for use as control inputs in Cosmos Transfer.
    """
    
    def __init__(self, config: Optional[ControlGenerationConfig] = None):
        """
        Initialize the control modality generator.
        
        Args:
            config: Configuration for generation
        """
        self.config = config or ControlGenerationConfig()
        self.device = self._get_device()
        self.models = {}
        self._lazy_load_models = True  # Load models only when needed
    
    def _get_device(self) -> str:
        """Get the device to use for inference."""
        if self.config.use_gpu and torch.cuda.is_available():
            return "cuda"
        return "cpu"
    
    def _load_depth_model(self):
        """Load depth estimation model (MiDaS)."""
        if 'depth' in self.models:
            return
        
        logger.info("Loading depth estimation model...")
        
        try:
            # Use MiDaS small model for speed
            model_type = "DPT_Hybrid"  # Or "MiDaS_small" for faster inference
            midas = torch.hub.load("intel-isl/MiDaS", model_type)
            midas.to(self.device)
            midas.eval()
            
            # Load transforms
            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
            transform = midas_transforms.dpt_transform
            
            self.models['depth'] = {
                'model': midas,
                'transform': transform
            }
            
            logger.info("Depth model loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load MiDaS model: {e}")
            logger.info("Falling back to simple depth approximation")
            self.models['depth'] = None
    
    def _load_segmentation_model(self):
        """Load semantic segmentation model (DeepLabV3)."""
        if 'segmentation' in self.models:
            return
        
        logger.info("Loading segmentation model...")
        
        try:
            # Use DeepLabV3 with ResNet50 backbone for balance of speed and accuracy
            model = torch.hub.load(
                'pytorch/vision:v0.10.0',
                'deeplabv3_resnet50',
                pretrained=True
            )
            model.to(self.device)
            model.eval()
            
            # Define transforms
            preprocess = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                ),
            ])
            
            self.models['segmentation'] = {
                'model': model,
                'transform': preprocess
            }
            
            logger.info("Segmentation model loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load segmentation model: {e}")
            logger.info("Falling back to simple segmentation")
            self.models['segmentation'] = None
    
    def generate_depth(
        self,
        input_video: Path,
        output_path: Path,
        single_frame: bool = False
    ) -> bool:
        """
        Generate depth estimation video.
        
        Args:
            input_video: Path to input video
            output_path: Path for output depth video
            single_frame: If True, only process middle frame
            
        Returns:
            True if successful, False otherwise
        """
        # Load model if needed
        if self._lazy_load_models:
            self._load_depth_model()
        
        # Open input video
        cap = cv2.VideoCapture(str(input_video))
        if not cap.isOpened():
            logger.error(f"Cannot open video: {input_video}")
            return False
        
        try:
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Setup output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            
            if single_frame or self.config.single_frame_mode:
                # Process only middle frame and repeat
                middle_idx = frame_count // 2
                cap.set(cv2.CAP_PROP_POS_FRAMES, middle_idx)
                ret, frame = cap.read()
                
                if ret:
                    depth_frame = self._process_depth_frame(frame)
                    depth_frame = cv2.resize(depth_frame, (width, height))
                    
                    # Write same frame for entire video
                    for _ in range(frame_count):
                        out.write(depth_frame)
            else:
                # Process all frames
                frame_idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    if frame_idx % self.config.extract_every_n_frames == 0:
                        depth_frame = self._process_depth_frame(frame)
                    
                    depth_frame = cv2.resize(depth_frame, (width, height))
                    out.write(depth_frame)
                    
                    frame_idx += 1
            
            logger.info(f"Depth video saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating depth video: {e}")
            return False
            
        finally:
            cap.release()
            if 'out' in locals():
                out.release()
    
    def _process_depth_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process a single frame for depth estimation.
        
        Args:
            frame: Input frame (BGR)
            
        Returns:
            Depth map as BGR image
        """
        if self.models.get('depth') is None:
            # Fallback: Simple depth approximation using luminance
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            depth = cv2.GaussianBlur(gray, (21, 21), 0)
            depth_colored = cv2.applyColorMap(depth, cv2.COLORMAP_MAGMA)
            return depth_colored
        
        try:
            # Use MiDaS model
            model_data = self.models['depth']
            
            # Prepare input
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            input_batch = model_data['transform'](img).to(self.device)
            
            # Inference
            with torch.no_grad():
                prediction = model_data['model'](input_batch)
                
                # Resize to original resolution
                prediction = torch.nn.functional.interpolate(
                    prediction.unsqueeze(1),
                    size=frame.shape[:2],
                    mode="bicubic",
                    align_corners=False,
                ).squeeze()
            
            # Convert to numpy and normalize
            depth = prediction.cpu().numpy()
            depth = (depth - depth.min()) / (depth.max() - depth.min()) * 255
            depth = depth.astype(np.uint8)
            
            # Apply colormap
            depth_colored = cv2.applyColorMap(depth, cv2.COLORMAP_MAGMA)
            
            return depth_colored
            
        except Exception as e:
            logger.warning(f"Depth processing failed, using fallback: {e}")
            # Fallback to simple method
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            depth = cv2.GaussianBlur(gray, (21, 21), 0)
            depth_colored = cv2.applyColorMap(depth, cv2.COLORMAP_MAGMA)
            return depth_colored
    
    def generate_segmentation(
        self,
        input_video: Path,
        output_path: Path,
        single_frame: bool = False
    ) -> bool:
        """
        Generate semantic segmentation video.
        
        Args:
            input_video: Path to input video
            output_path: Path for output segmentation video
            single_frame: If True, only process middle frame
            
        Returns:
            True if successful, False otherwise
        """
        # Load model if needed
        if self._lazy_load_models:
            self._load_segmentation_model()
        
        # Open input video
        cap = cv2.VideoCapture(str(input_video))
        if not cap.isOpened():
            logger.error(f"Cannot open video: {input_video}")
            return False
        
        try:
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Setup output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            
            if single_frame or self.config.single_frame_mode:
                # Process only middle frame
                middle_idx = frame_count // 2
                cap.set(cv2.CAP_PROP_POS_FRAMES, middle_idx)
                ret, frame = cap.read()
                
                if ret:
                    seg_frame = self._process_segmentation_frame(frame)
                    seg_frame = cv2.resize(seg_frame, (width, height))
                    
                    # Write same frame for entire video
                    for _ in range(frame_count):
                        out.write(seg_frame)
            else:
                # Process all frames
                frame_idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    if frame_idx % self.config.extract_every_n_frames == 0:
                        seg_frame = self._process_segmentation_frame(frame)
                    
                    seg_frame = cv2.resize(seg_frame, (width, height))
                    out.write(seg_frame)
                    
                    frame_idx += 1
            
            logger.info(f"Segmentation video saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating segmentation video: {e}")
            return False
            
        finally:
            cap.release()
            if 'out' in locals():
                out.release()
    
    def _process_segmentation_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process a single frame for segmentation.
        
        Args:
            frame: Input frame (BGR)
            
        Returns:
            Segmentation map as BGR image
        """
        if self.models.get('segmentation') is None:
            # Fallback: Simple color-based segmentation
            return self._simple_segmentation(frame)
        
        try:
            # Use DeepLabV3 model
            model_data = self.models['segmentation']
            
            # Prepare input
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img)
            input_tensor = model_data['transform'](img_pil)
            input_batch = input_tensor.unsqueeze(0).to(self.device)
            
            # Inference
            with torch.no_grad():
                output = model_data['model'](input_batch)['out'][0]
                output_predictions = output.argmax(0)
            
            # Convert to colored segmentation map
            seg_map = output_predictions.byte().cpu().numpy()
            
            # Create color map (21 classes for PASCAL VOC)
            colors = self._get_pascal_voc_colors()
            seg_colored = np.zeros((seg_map.shape[0], seg_map.shape[1], 3), dtype=np.uint8)
            
            for class_id in range(21):
                seg_colored[seg_map == class_id] = colors[class_id]
            
            return seg_colored
            
        except Exception as e:
            logger.warning(f"Segmentation processing failed, using fallback: {e}")
            return self._simple_segmentation(frame)
    
    def _simple_segmentation(self, frame: np.ndarray) -> np.ndarray:
        """
        Simple fallback segmentation using color clustering.
        
        Args:
            frame: Input frame
            
        Returns:
            Segmentation map
        """
        # Convert to LAB color space
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        
        # Simple k-means clustering
        Z = lab.reshape((-1, 3))
        Z = np.float32(Z)
        
        # Define criteria and apply kmeans
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        K = 8  # Number of clusters
        ret, label, center = cv2.kmeans(Z, K, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # Convert back to uint8 and make color image
        center = np.uint8(center)
        res = center[label.flatten()]
        res2 = res.reshape((frame.shape))
        
        # Convert back to BGR
        seg_colored = cv2.cvtColor(res2, cv2.COLOR_LAB2BGR)
        
        return seg_colored
    
    def _get_pascal_voc_colors(self) -> np.ndarray:
        """Get PASCAL VOC color palette."""
        colors = np.array([
            [0, 0, 0],        # Background
            [128, 0, 0],      # Aeroplane
            [0, 128, 0],      # Bicycle
            [128, 128, 0],    # Bird
            [0, 0, 128],      # Boat
            [128, 0, 128],    # Bottle
            [0, 128, 128],    # Bus
            [128, 128, 128],  # Car
            [64, 0, 0],       # Cat
            [192, 0, 0],      # Chair
            [64, 128, 0],     # Cow
            [192, 128, 0],    # Dining table
            [64, 0, 128],     # Dog
            [192, 0, 128],    # Horse
            [64, 128, 128],   # Motorbike
            [192, 128, 128],  # Person
            [0, 64, 0],       # Potted plant
            [128, 64, 0],     # Sheep
            [0, 192, 0],      # Sofa
            [128, 192, 0],    # Train
            [0, 64, 128]      # TV/Monitor
        ])
        return colors
    
    def generate_edge(
        self,
        input_video: Path,
        output_path: Path,
        low_threshold: Optional[int] = None,
        high_threshold: Optional[int] = None
    ) -> bool:
        """
        Generate edge detection video using Canny edge detection.
        
        Args:
            input_video: Path to input video
            output_path: Path for output edge video
            low_threshold: Low threshold for Canny
            high_threshold: High threshold for Canny
            
        Returns:
            True if successful, False otherwise
        """
        # Use config thresholds if not provided
        low_threshold = low_threshold or self.config.edge_threshold_low
        high_threshold = high_threshold or self.config.edge_threshold_high
        
        # Open input video
        cap = cv2.VideoCapture(str(input_video))
        if not cap.isOpened():
            logger.error(f"Cannot open video: {input_video}")
            return False
        
        try:
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Setup output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Convert to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Apply Gaussian blur to reduce noise
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                
                # Apply Canny edge detection
                edges = cv2.Canny(blurred, low_threshold, high_threshold)
                
                # Convert back to BGR for video writing
                edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
                
                out.write(edges_bgr)
            
            logger.info(f"Edge video saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating edge video: {e}")
            return False
            
        finally:
            cap.release()
            if 'out' in locals():
                out.release()
    
    def generate_all_modalities(
        self,
        input_video: Path,
        output_dir: Path,
        single_frame_mode: bool = False
    ) -> Dict[str, Path]:
        """
        Generate all control modalities for a video.
        
        Args:
            input_video: Path to input video
            output_dir: Directory for output videos
            single_frame_mode: If True, only process middle frame for speed
            
        Returns:
            Dictionary mapping modality names to output paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        
        # Generate depth
        depth_path = output_dir / "depth.mp4"
        if self.generate_depth(input_video, depth_path, single_frame_mode):
            results['depth'] = depth_path
        
        # Generate segmentation
        seg_path = output_dir / "segmentation.mp4"
        if self.generate_segmentation(input_video, seg_path, single_frame_mode):
            results['seg'] = seg_path
        
        # Generate edge
        edge_path = output_dir / "edge.mp4"
        if self.generate_edge(input_video, edge_path):
            results['edge'] = edge_path
        
        return results


def main():
    """Example usage of control modality generation."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python control_generator.py <input_video> <output_dir>")
        sys.exit(1)
    
    input_video = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    # Create generator with config for speed
    config = ControlGenerationConfig(
        single_frame_mode=True,  # Fast mode for testing
        use_gpu=torch.cuda.is_available()
    )
    
    generator = ControlModalityGenerator(config)
    
    print("Generating control modalities...")
    print(f"Input: {input_video}")
    print(f"Output: {output_dir}")
    print(f"Mode: {'Single Frame' if config.single_frame_mode else 'Full Video'}")
    print(f"Device: {generator.device}")
    print("-" * 50)
    
    results = generator.generate_all_modalities(
        input_video,
        output_dir,
        single_frame_mode=config.single_frame_mode
    )
    
    print("\nGenerated modalities:")
    for modality, path in results.items():
        print(f"  {modality}: {path}")
    
    if not results:
        print("  No modalities generated successfully")


if __name__ == "__main__":
    main()