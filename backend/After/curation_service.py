import cv2
import numpy as np
import mediapipe as mp
from PIL import Image

class CurationService:
    def __init__(self):
        try:
            print("init MediaPipe...")
            self.mp_face_detection = mp.solutions.face_detection
            self.face_detection = self.mp_face_detection.FaceDetection(
                min_detection_confidence=0.5,
                model_selection=0
            )
            print("MediaPipe Init Success")
        except Exception as e:
            print(f"CRITICAL: MediaPipe failed to load: {e}")
            self.face_detection = None

    def calculate_score(self, image_input) -> float:
        try:
            image_bgr = None

            # Convert PIL -> OpenCV (BGR)
            if isinstance(image_input, Image.Image):
                if image_input.mode != 'RGB':
                    image_input = image_input.convert('RGB')
                image_bgr = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
            
            elif isinstance(image_input, str):
                image_bgr = cv2.imread(image_input)

            if image_bgr is None:
                print("Curation: Image is None")
                return 0.0

            return self._calculate_internal(image_bgr)

        except Exception as e:
            print(f"Curation Crash: {e}")
            return 0.0

    def _calculate_internal(self, image_bgr) -> float:
        """
        🎨 IMPROVED: Multi-dimensional quality assessment
        """
        try:
            # Resize for consistent processing
            h, w = image_bgr.shape[:2]
            if max(h, w) > 1024:
                scale = 1024 / max(h, w)
                image_bgr = cv2.resize(image_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            
            # Convert to different color spaces
            gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
            
            # ═══════════════════════════════════════════════════
            # 1. SHARPNESS / BLUR (Weight: 20%)
            # ═══════════════════════════════════════════════════
            score_sharpness = self._calculate_sharpness(gray)
            
            # ═══════════════════════════════════════════════════
            # 2. EXPOSURE / BRIGHTNESS (Weight: 15%)
            # ═══════════════════════════════════════════════════
            score_exposure = self._calculate_exposure(hsv)
            
            # ═══════════════════════════════════════════════════
            # 3. COLOR VIBRANCY (Weight: 15%)
            # ═══════════════════════════════════════════════════
            score_color = self._calculate_color_quality(hsv)
            
            # ═══════════════════════════════════════════════════
            # 4. COMPOSITION (Weight: 15%)
            # ═══════════════════════════════════════════════════
            score_composition = self._calculate_composition(gray)
            
            # ═══════════════════════════════════════════════════
            # 5. CONTRAST (Weight: 10%)
            # ═══════════════════════════════════════════════════
            score_contrast = self._calculate_contrast(gray)
            
            # ═══════════════════════════════════════════════════
            # 6. DETAIL / TEXTURE (Weight: 10%)
            # ═══════════════════════════════════════════════════
            score_detail = self._calculate_detail(gray)
            
            # ═══════════════════════════════════════════════════
            # 7. FACE PRESENCE (Weight: 15%)
            # ═══════════════════════════════════════════════════
            score_face = self._calculate_face_score(image_bgr)
            
            # ═══════════════════════════════════════════════════
            # FINAL WEIGHTED SCORE
            # ═══════════════════════════════════════════════════
            total = (
                score_sharpness * 0.20 +
                score_exposure * 0.15 +
                score_color * 0.20 +
                score_composition * 0.20 +
                score_contrast * 0.15 +
                score_detail * 0.05 +
                score_face * 0.05
            )
            
            return round(total, 4)

        except Exception as e:
            print(f"Internal Calc Failed: {e}")
            return 0.0

    # ═══════════════════════════════════════════════════════════
    # QUALITY METRICS (Individual Scorers)
    # ═══════════════════════════════════════════════════════════

    def _calculate_sharpness(self, gray: np.ndarray) -> float:
        """
        🎨 IMPROVED: Multi-method blur detection
        Combines Laplacian variance with gradient magnitude
        """
        try:
            # Method 1: Laplacian variance (edge detection)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            laplacian_var = laplacian.var()
            
            # Method 2: Gradient magnitude (Sobel)
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(sobelx**2 + sobely**2).mean()
            
            # Normalize both metrics
            lap_score = min(laplacian_var / 500.0, 1.0)
            grad_score = min(gradient_magnitude / 50.0, 1.0)
            
            # Combined sharpness score
            sharpness = (lap_score * 0.6) + (grad_score * 0.4)
            
            return float(sharpness)
        except:
            return 0.5

    def _calculate_exposure(self, hsv: np.ndarray) -> float:
        """
        🎨 IMPROVED: Advanced exposure analysis
        Checks histogram distribution, not just mean brightness
        """
        try:
            v_channel = hsv[:, :, 2]
            
            # Mean brightness
            mean_brightness = v_channel.mean()
            
            # Histogram analysis
            hist, _ = np.histogram(v_channel, bins=256, range=(0, 256))
            hist = hist / hist.sum()  # Normalize
            
            # Check for clipping (overexposure/underexposure)
            shadow_clip = hist[:10].sum()  # Dark pixels (0-10)
            highlight_clip = hist[-10:].sum()  # Bright pixels (246-255)
            
            # Penalize clipping
            clipping_penalty = max(shadow_clip, highlight_clip) * 2
            
            # Optimal brightness range: 100-160 (darker than before for better aesthetics)
            brightness_score = 1.0 - (abs(mean_brightness - 130) / 130.0)
            brightness_score = max(0.0, brightness_score)
            
            # Penalize heavily clipped images
            final_score = brightness_score * (1.0 - clipping_penalty)
            
            return max(0.0, min(1.0, final_score))
        except:
            return 0.5

    def _calculate_color_quality(self, hsv: np.ndarray) -> float:
        """
        🎨 NEW: Color vibrancy and diversity
        Vibrant, diverse colors = more visually appealing
        """
        try:
            h_channel = hsv[:, :, 0]  # Hue
            s_channel = hsv[:, :, 1]  # Saturation
            
            # Saturation score (vibrant colors)
            mean_saturation = s_channel.mean()
            saturation_score = min(mean_saturation / 180.0, 1.0)
            
            # Color diversity (unique hues)
            hist_hue, _ = np.histogram(h_channel, bins=36, range=(0, 180))
            hist_hue = hist_hue / hist_hue.sum()
            
            # Entropy: high entropy = diverse colors
            entropy = -np.sum(hist_hue * np.log2(hist_hue + 1e-7))
            max_entropy = np.log2(36)  # Maximum possible entropy
            diversity_score = entropy / max_entropy
            
            # Combined color score
            color_score = (saturation_score * 0.6) + (diversity_score * 0.4)
            
            return float(color_score)
        except:
            return 0.5

    def _calculate_composition(self, gray: np.ndarray) -> float:
        """
        🎨 NEW: Rule of thirds and visual balance
        Checks if subjects are positioned well
        """
        try:
            h, w = gray.shape
            
            # Divide image into 3x3 grid (rule of thirds)
            grid_h = h // 3
            grid_w = w // 3
            
            # Calculate edge density in each region
            edges = cv2.Canny(gray, 50, 150)
            
            # 4 power points (intersections of rule of thirds lines)
            power_points = [
                edges[grid_h:2*grid_h, grid_w:2*grid_w],  # Center
                edges[grid_h:2*grid_h, 0:grid_w],         # Left-center
                edges[grid_h:2*grid_h, 2*grid_w:],        # Right-center
                edges[0:grid_h, grid_w:2*grid_w],         # Top-center
                edges[2*grid_h:, grid_w:2*grid_w]         # Bottom-center
            ]
            
            # Calculate edge density at power points
            power_density = [region.sum() / region.size for region in power_points]
            max_density = max(power_density)
            
            # Check if image has good balance (not all weight on one side)
            left_weight = edges[:, :w//2].sum()
            right_weight = edges[:, w//2:].sum()
            total_weight = left_weight + right_weight
            
            if total_weight > 0:
                balance = 1.0 - abs(float(left_weight) - float(right_weight)) / total_weight
            else:
                balance = 0.5
            
            # Composition score
            composition = (max_density / 255.0) * 0.7 + balance * 0.3
            
            return min(1.0, composition)
        except:
            return 0.5

    def _calculate_contrast(self, gray: np.ndarray) -> float:
        """
        🎨 IMPROVED: Dynamic range analysis
        Good photos have a full range of tones
        """
        try:
            # Standard deviation as contrast measure
            std_dev = gray.std()
            contrast_score = min(std_dev / 70.0, 1.0)
            
            # Histogram spread (uses full tonal range?)
            hist, _ = np.histogram(gray, bins=256, range=(0, 256))
            non_zero_bins = np.count_nonzero(hist)
            spread_score = non_zero_bins / 256.0
            
            # Combined contrast
            contrast = (contrast_score * 0.7) + (spread_score * 0.3)
            
            return float(contrast)
        except:
            return 0.5

    def _calculate_detail(self, gray: np.ndarray) -> float:
        """
        🎨 NEW: Texture and fine detail analysis
        Photos with rich detail are more interesting
        """
        try:
            # High-frequency content (fine details)
            # Use high-pass filter
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            high_freq = cv2.subtract(gray, blurred)
            
            # Measure detail
            detail_amount = high_freq.std()
            detail_score = min(detail_amount / 30.0, 1.0)
            
            return float(detail_score)
        except:
            return 0.5

    def _calculate_face_score(self, image_bgr: np.ndarray) -> float:
        """
        🎨 IMPROVED: Sophisticated face scoring
        Considers face size, position, and multiple faces
        """
        if not self.face_detection:
            return 0.0
        
        try:
            img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            results = self.face_detection.process(img_rgb)
            
            if not results.detections:
                return 0.0
            
            h, w = img_rgb.shape[:2]
            face_scores = []
            
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                
                # Face size (larger = better for portraits)
                face_area = bbox.width * bbox.height
                size_score = min(face_area * 4, 1.0)  # Optimal around 25% of image
                
                # Face position (center is better)
                face_center_x = bbox.xmin + bbox.width / 2
                face_center_y = bbox.ymin + bbox.height / 2
                
                # Distance from image center
                dist_from_center = np.sqrt((face_center_x - 0.5)**2 + (face_center_y - 0.5)**2)
                position_score = max(0.0, 1.0 - dist_from_center * 2)
                
                # Detection confidence
                confidence = detection.score[0] if detection.score else 0.5
                
                # Combined face score
                face_score = (size_score * 0.4) + (position_score * 0.3) + (confidence * 0.3)
                face_scores.append(face_score)
            
            # Return best face score (or average if multiple good faces)
            if len(face_scores) == 1:
                return face_scores[0]
            else:
                # Multiple faces: average of top 2
                face_scores.sort(reverse=True)
                return np.mean(face_scores[:2])
        
        except Exception as e:
            print(f"Face detection error: {e}")
            return 0.0