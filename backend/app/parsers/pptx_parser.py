"""
PowerPoint Org Chart Parser with Outside-Canvas Support.

CRITICAL: This parser processes ALL shapes regardless of position, including:
- Shapes with negative X/Y coordinates (positioned left/above canvas)
- Shapes extending beyond slide boundaries
- Shapes partially or fully outside the visible canvas

Analysis of real-world org charts (e.g., Pax_Org_Chart.pptx) revealed that 38% of shapes
are positioned OUTSIDE the visible slide canvas. Standard parsers that filter by slide
boundaries will miss critical org chart nodes.

Features:
- Processes ALL shapes regardless of position (no boundary filtering)
- Uses relative spatial positioning, not absolute canvas boundaries
- Fuzzy level inference via K-Means clustering on Y-coordinates
- Connector line detection for manager-employee relationships
- Handles disconnected forests (multiple root nodes)
"""

from pptx import Presentation
from pptx.util import Inches, Emu
from pptx.enum.shapes import MSO_SHAPE_TYPE
from typing import List, Dict, Tuple, Optional, Any
import networkx as nx
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

# EMU (English Metric Units) conversion: 914400 EMUs = 1 inch
EMU_PER_INCH = 914400


@dataclass
class ParsedEmployee:
    """Represents a parsed org chart node."""
    id: str
    name: str
    title: str
    grade: Optional[str] = None
    full_text: str = ""
    level: int = 0
    position: Dict[str, float] = field(default_factory=dict)
    font_size: float = 12.0
    slide_index: int = 0
    shape_type: str = "unknown"
    fill_color: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # Add full_name for consistency with API expectations
        result["full_name"] = result["name"]
        result["job_title"] = result["title"]
        return result


@dataclass
class ParseResult:
    """Result of parsing a PowerPoint file."""
    employees: List[Dict[str, Any]]
    relationships: List[Tuple[str, str]]
    forests: List[Dict[str, Any]]
    unassigned: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    graph: Optional[nx.DiGraph] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "employees": self.employees,
            "relationships": [list(r) for r in self.relationships],
            "forests": self.forests,
            "unassigned": self.unassigned,
            "metadata": self.metadata,
        }


class OrgChartParser:
    """
    Parses PowerPoint org charts, including shapes OUTSIDE visible canvas.

    Key Features:
    - Processes ALL shapes regardless of position (including negative coordinates)
    - Uses relative spatial positioning, not absolute canvas boundaries
    - Fuzzy level inference via K-Means clustering on Y-coordinates
    - Connector line detection for manager-employee relationships
    - Handles disconnected forests (multiple root nodes)
    """

    def __init__(
        self,
        pptx_path: str,
        max_horizontal_distance_inches: float = 8.0,  # Increased for wide org charts
        min_text_length: int = 2,
        max_levels: int = 12,
        filter_title_boxes: bool = True,
    ):
        """
        Initialize the parser with a PowerPoint file.

        Args:
            pptx_path: Path to the .pptx file
            max_horizontal_distance_inches: Max horizontal distance for manager assignment
            min_text_length: Minimum text length to consider a shape valid
            max_levels: Maximum hierarchy levels to detect
            filter_title_boxes: Whether to filter out slide title boxes (default True)
        """
        self.pptx_path = Path(pptx_path)
        if not self.pptx_path.exists():
            raise FileNotFoundError(f"PPTX file not found: {pptx_path}")

        self.presentation = Presentation(pptx_path)
        self.slide_width = self.presentation.slide_width
        self.slide_height = self.presentation.slide_height
        self.max_horizontal_distance = max_horizontal_distance_inches * EMU_PER_INCH
        self.min_text_length = min_text_length
        self.max_levels = max_levels
        self.filter_title_boxes = filter_title_boxes

    def parse(self) -> ParseResult:
        """
        Parse all slides and return structured org data.

        Returns:
            ParseResult containing:
            - employees: List of all parsed employee nodes
            - relationships: List of (manager_id, employee_id) edges
            - forests: Separate org trees if multiple roots
            - unassigned: Orphaned nodes
            - metadata: Slide dimensions, parse stats
        """
        all_employees: List[ParsedEmployee] = []
        all_relationships: List[Tuple[str, str]] = []
        connectors: List[Dict] = []
        all_filtered_titles: List[str] = []

        for slide_idx, slide in enumerate(self.presentation.slides):
            slide_data = self._parse_slide(slide, slide_idx)
            all_employees.extend(slide_data["employees"])
            connectors.extend(slide_data.get("connectors", []))
            all_filtered_titles.extend(slide_data.get("filtered_titles", []))

        # Convert to dicts for processing
        employee_dicts = [emp.to_dict() for emp in all_employees]

        # Infer relationships from connectors first, then spatial proximity
        if connectors:
            connector_relationships = self._infer_relationships_from_connectors(
                employee_dicts, connectors
            )
            all_relationships.extend(connector_relationships)

        # Fill in remaining relationships using spatial proximity
        spatial_relationships = self._infer_relationships_spatial(
            employee_dicts, set(all_relationships)
        )
        all_relationships.extend(spatial_relationships)

        # Build graph and identify forests
        result = self._build_org_graph(employee_dicts, all_relationships)

        # Calculate ACTUAL hierarchy depth from graph structure
        # This is the true organizational layers count, not K-Means clustering estimate
        actual_hierarchy_depth = self._calculate_hierarchy_depth(result.graph)

        # Reassign levels to employees based on actual graph depth from root
        self._assign_graph_based_levels(result.graph, employee_dicts)

        # Calculate metadata
        outside_canvas_count = len([
            emp for emp in employee_dicts
            if emp["position"]["left"] < 0 or
               emp["position"]["top"] < 0 or
               emp["position"]["right"] > self.slide_width or
               emp["position"]["bottom"] > self.slide_height
        ])

        # Use actual graph-based hierarchy depth, not K-Means clustering
        result.metadata = {
            "total_slides": len(self.presentation.slides),
            "total_employees": len(employee_dicts),
            "total_relationships": len(all_relationships),
            "levels_detected": actual_hierarchy_depth,  # Actual org layers from graph
            "slide_dimensions": {
                "width_emu": self.slide_width,
                "height_emu": self.slide_height,
                "width_inches": self.slide_width / EMU_PER_INCH,
                "height_inches": self.slide_height / EMU_PER_INCH,
            },
            "outside_canvas_count": outside_canvas_count,
            "outside_canvas_percentage": (
                outside_canvas_count / len(employee_dicts) * 100
                if employee_dicts else 0
            ),
            "forest_count": len(result.forests),
            "orphan_count": len(result.unassigned),
            "source_file": str(self.pptx_path.name),
            "filtered_title_boxes": all_filtered_titles,
            "filtered_title_count": len(all_filtered_titles),
        }

        return result

    def _parse_slide(self, slide, slide_idx: int) -> Dict:
        """
        Parse a single slide, extracting all text shapes regardless of position.

        CRITICAL: Do NOT filter by canvas boundaries. Process shapes with negative
        coordinates or those extending beyond slide edges.
        """
        text_boxes: List[ParsedEmployee] = []
        connectors: List[Dict] = []
        shape_counter = [0]  # Use list for mutable counter in nested function

        def process_shape(shape, parent_offset_x: float = 0, parent_offset_y: float = 0):
            """Process a shape, recursively handling groups."""
            shape_idx = shape_counter[0]
            shape_counter[0] += 1

            # Check if this is a group shape (including SmartArt)
            if hasattr(shape, "shapes"):
                # This is a grouped shape - process all child shapes
                group_left = getattr(shape, "left", 0) or 0
                group_top = getattr(shape, "top", 0) or 0

                for child_shape in shape.shapes:
                    # Pass the group's position as offset for child shapes
                    process_shape(
                        child_shape,
                        parent_offset_x + group_left,
                        parent_offset_y + group_top
                    )
                return

            # Collect connector lines for relationship inference
            if hasattr(shape, "begin_x") and hasattr(shape, "end_x"):
                connectors.append({
                    "begin_x": (getattr(shape, "begin_x", 0) or 0) + parent_offset_x,
                    "begin_y": (getattr(shape, "begin_y", 0) or 0) + parent_offset_y,
                    "end_x": (getattr(shape, "end_x", 0) or 0) + parent_offset_x,
                    "end_y": (getattr(shape, "end_y", 0) or 0) + parent_offset_y,
                })
                return

            # Only process shapes with text content
            if not hasattr(shape, "text") or not shape.text:
                return

            text = shape.text.strip()
            if len(text) < self.min_text_length:
                return

            # Extract position (INCLUDING negative coordinates)
            # Add parent offset for grouped shapes
            left = (getattr(shape, "left", 0) or 0) + parent_offset_x
            top = (getattr(shape, "top", 0) or 0) + parent_offset_y
            width = getattr(shape, "width", 0) or 0
            height = getattr(shape, "height", 0) or 0
            right = left + width
            bottom = top + height

            # Extract text lines
            text_lines = [
                line.strip()
                for line in text.split("\n")
                if line.strip()
            ]

            # Heuristic: First line = Name, Second line = Title, Third line = Grade/Level
            name = text_lines[0] if text_lines else f"Unknown_{slide_idx}_{shape_idx}"
            title = text_lines[1] if len(text_lines) > 1 else "Unknown Title"
            grade = text_lines[2] if len(text_lines) > 2 else None

            # Extract font size (for level inference)
            font_size = self._extract_font_size(shape)

            # Extract fill color if available
            fill_color = self._extract_fill_color(shape)

            # Determine shape type
            shape_type = self._get_shape_type(shape)

            employee = ParsedEmployee(
                id=f"slide{slide_idx}_shape{shape_idx}",
                name=name,
                title=title,
                grade=grade,
                full_text=text,
                position={
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                    "right": right,
                    "bottom": bottom,
                    "center_x": left + width / 2,
                    "center_y": top + height / 2,
                    "left_inches": left / EMU_PER_INCH,
                    "top_inches": top / EMU_PER_INCH,
                    "width_inches": width / EMU_PER_INCH,
                    "height_inches": height / EMU_PER_INCH,
                },
                font_size=font_size,
                slide_index=slide_idx,
                shape_type=shape_type,
                fill_color=fill_color,
                metadata={
                    "text_line_count": len(text_lines),
                    "all_text_lines": text_lines,
                },
            )

            text_boxes.append(employee)

        # Process all shapes on the slide (recursively for groups)
        for shape in slide.shapes:
            process_shape(shape)

        # Filter out title boxes if enabled
        filtered_text_boxes = text_boxes
        filtered_titles = []
        if self.filter_title_boxes and text_boxes:
            filtered_text_boxes = []
            for emp in text_boxes:
                position = {
                    "top": emp.position["top"],
                    "width": emp.position["width"],
                }
                text_lines = emp.metadata.get("all_text_lines", [emp.name])
                if self._is_title_box(
                    emp.full_text,
                    text_lines,
                    position,
                    emp.font_size,
                    text_boxes,  # Pass all boxes for font comparison
                ):
                    filtered_titles.append(emp.full_text)
                else:
                    filtered_text_boxes.append(emp)

            if filtered_titles:
                logger.info(
                    f"Filtered {len(filtered_titles)} title box(es) from slide {slide_idx}: "
                    f"{filtered_titles}"
                )

        # Infer hierarchy levels using K-Means clustering
        if filtered_text_boxes:
            levels = self._infer_hierarchy_levels(filtered_text_boxes)
            for emp in filtered_text_boxes:
                emp.level = levels.get(emp.id, 1)

        return {
            "employees": filtered_text_boxes,
            "connectors": connectors,
            "filtered_titles": filtered_titles,
        }

    def _extract_font_size(self, shape) -> float:
        """Extract the primary font size from a shape."""
        font_size = 12.0  # Default

        try:
            if hasattr(shape, "text_frame"):
                for paragraph in shape.text_frame.paragraphs:
                    if paragraph.runs:
                        run = paragraph.runs[0]
                        if run.font.size:
                            font_size = run.font.size.pt
                            break
        except Exception:
            pass

        return font_size

    def _extract_fill_color(self, shape) -> Optional[str]:
        """Extract the fill color from a shape."""
        try:
            if hasattr(shape, "fill") and shape.fill.type is not None:
                fore_color = shape.fill.fore_color
                if hasattr(fore_color, "rgb") and fore_color.rgb:
                    return str(fore_color.rgb)
        except Exception:
            pass
        return None

    def _get_shape_type(self, shape) -> str:
        """Determine the shape type."""
        try:
            if hasattr(shape, "shape_type"):
                return str(shape.shape_type)
        except Exception:
            pass
        return "unknown"

    def _is_title_box(
        self,
        text: str,
        text_lines: List[str],
        position: Dict,
        font_size: float,
        all_text_boxes: List["ParsedEmployee"],
    ) -> bool:
        """
        Determine if a shape is a slide title box rather than an employee box.

        Title boxes typically have these characteristics:
        - Single line of text (no name/title/grade structure)
        - Located at the top of the slide
        - Wide width spanning significant portion of slide
        - Larger font size than typical employee boxes
        - Common title keywords like "Department", "Organization", "Team", etc.
        - Company/brand names followed by organizational terms
        """
        # Common title keywords that indicate a slide title, not an employee
        title_keywords = [
            "department", "organization", "org chart", "orgchart", "structure",
            "team", "division", "services", "unit", "branch", "section",
            "hierarchy", "reporting", "chart", "overview", "company",
            "corporate", "group", "operations", "management", "function",
            "directorate", "office", "centre", "center", "passenger",
            "cargo", "logistics", "aviation", "airport", "airline",
        ]

        # Common company/brand names that may appear in titles
        company_indicators = [
            "sats", "ltd", "pte", "inc", "corp", "limited", "holdings",
            "international", "global", "asia", "pacific",
        ]

        text_lower = text.lower().strip()

        # Check 1: Single line of text is a strong indicator of title box
        # Employee boxes typically have 2-3 lines (name, title, grade)
        is_single_line = len(text_lines) == 1

        # Check 2: Contains title keywords
        has_title_keyword = any(kw in text_lower for kw in title_keywords)

        # Check 2b: Contains company indicators combined with org terms
        has_company_with_org = (
            any(ci in text_lower for ci in company_indicators) and
            any(kw in text_lower for kw in title_keywords)
        )

        # Check 3: Position is at the very top of the slide (top 15% of slide height)
        # Increased from 10% to 15% to catch more title boxes
        top_threshold = self.slide_height * 0.15
        is_at_top = position["top"] < top_threshold

        # Check 4: Width spans more than 40% of slide width (typical for titles)
        # Reduced from 50% to 40% to catch more title boxes
        width_ratio = position["width"] / self.slide_width if self.slide_width > 0 else 0
        is_wide = width_ratio > 0.40

        # Check 5: Font size comparison - title boxes usually have larger fonts
        # Compare with average font size of other boxes if available
        has_large_font = False
        if all_text_boxes:
            # Use median instead of mean for better outlier handling
            sorted_fonts = sorted(e.font_size for e in all_text_boxes)
            median_font_size = sorted_fonts[len(sorted_fonts) // 2]
            has_large_font = font_size > median_font_size * 1.2  # 20% larger than median

        # Check 6: Text pattern analysis
        # Employee names are typically 2-3 words, not long phrases
        word_count = len(text.split())
        has_many_words = word_count > 4

        # Check 7: Looks like a header phrase (contains "passenger services department" pattern)
        looks_like_header = bool(
            text_lower.endswith("department") or
            text_lower.endswith("services") or
            text_lower.endswith("division") or
            text_lower.endswith("team") or
            text_lower.endswith("unit") or
            text_lower.endswith("group") or
            text_lower.endswith("office")
        )

        # Decision logic:
        # - Single line + title keyword = very likely title
        # - Single line + at top + wide = likely title
        # - Single line + large font + at top = likely title
        # - Single line + company indicator + org term = likely title
        # - Single line + looks like header phrase = likely title
        if is_single_line:
            if has_title_keyword:
                logger.info(f"Filtering title box (keyword match): '{text}'")
                return True
            if has_company_with_org:
                logger.info(f"Filtering title box (company + org term): '{text}'")
                return True
            if looks_like_header:
                logger.info(f"Filtering title box (header phrase): '{text}'")
                return True
            if is_at_top and is_wide:
                logger.info(f"Filtering title box (top + wide): '{text}'")
                return True
            if has_large_font and is_at_top:
                logger.info(f"Filtering title box (large font + top): '{text}'")
                return True
            if is_at_top and has_many_words:
                logger.info(f"Filtering title box (top + many words): '{text}'")
                return True

        return False

    def _infer_hierarchy_levels(
        self, employees: List[ParsedEmployee]
    ) -> Dict[str, int]:
        """
        Use K-Means clustering on Y-coordinates and font sizes to determine levels.

        This handles varied slide layouts where strict pixel thresholds fail.
        """
        if not employees:
            return {}

        # Extract features: Y-coordinate (primary), font size (secondary)
        features = []
        for emp in employees:
            features.append([
                emp.position["center_y"],
                -emp.font_size,  # Negative because larger font = higher level
            ])

        features = np.array(features)

        # Normalize features
        scaler = StandardScaler()
        try:
            features_scaled = scaler.fit_transform(features)
        except Exception:
            # Fallback: use Y-coordinate only
            features_scaled = features[:, 0:1]

        # Estimate number of levels using a more conservative heuristic
        # Real org charts typically have 5-10 levels even with many employees
        # Use square root-based estimation with reasonable bounds
        n_samples = len(employees)
        # For 64 employees: sqrt(64) = 8, for 100 employees: sqrt(100) = 10
        # This gives more reasonable estimates than n_samples // 4
        estimated_levels = max(2, min(10, int(np.sqrt(n_samples))))
        n_levels = min(self.max_levels, estimated_levels)
        n_levels = min(n_levels, n_samples)  # Can't have more clusters than samples

        # K-Means clustering
        try:
            kmeans = KMeans(n_clusters=n_levels, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(features_scaled)

            # Sort clusters by average Y-coordinate (top to bottom = Level 1 to N)
            cluster_y_means = {}
            for i, emp in enumerate(employees):
                cluster = cluster_labels[i]
                if cluster not in cluster_y_means:
                    cluster_y_means[cluster] = []
                cluster_y_means[cluster].append(emp.position["center_y"])

            cluster_order = sorted(
                cluster_y_means.keys(),
                key=lambda c: np.mean(cluster_y_means[c])
            )

            # Map cluster labels to level numbers
            level_mapping = {
                old_label: new_level + 1
                for new_level, old_label in enumerate(cluster_order)
            }

            # Assign levels to employees
            result = {}
            for i, emp in enumerate(employees):
                cluster = cluster_labels[i]
                result[emp.id] = level_mapping[cluster]

            return result

        except Exception as e:
            logger.warning(f"K-Means clustering failed: {e}. Using fallback.")
            # Fallback: assign levels based on Y-coordinate percentiles
            y_coords = [emp.position["center_y"] for emp in employees]
            sorted_indices = np.argsort(y_coords)
            result = {}
            for rank, idx in enumerate(sorted_indices):
                level = min(self.max_levels, (rank * self.max_levels // len(employees)) + 1)
                result[employees[idx].id] = level
            return result

    def _infer_relationships_from_connectors(
        self,
        employees: List[Dict],
        connectors: List[Dict]
    ) -> List[Tuple[str, str]]:
        """Infer relationships from connector lines in the slide."""
        relationships = []

        for connector in connectors:
            begin_x = connector.get("begin_x", 0)
            begin_y = connector.get("begin_y", 0)
            end_x = connector.get("end_x", 0)
            end_y = connector.get("end_y", 0)

            # Find shapes closest to connector endpoints
            begin_emp = self._find_closest_employee(employees, begin_x, begin_y)
            end_emp = self._find_closest_employee(employees, end_x, end_y)

            if begin_emp and end_emp and begin_emp != end_emp:
                # Determine direction: higher level is manager
                if begin_emp["level"] < end_emp["level"]:
                    relationships.append((begin_emp["id"], end_emp["id"]))
                elif end_emp["level"] < begin_emp["level"]:
                    relationships.append((end_emp["id"], begin_emp["id"]))

        return relationships

    def _find_closest_employee(
        self,
        employees: List[Dict],
        x: float,
        y: float,
        max_distance: float = None
    ) -> Optional[Dict]:
        """Find the employee closest to the given coordinates."""
        if max_distance is None:
            max_distance = 2 * EMU_PER_INCH  # 2 inches

        closest = None
        min_dist = float("inf")

        for emp in employees:
            pos = emp["position"]
            # Check if point is inside or near the shape
            cx, cy = pos["center_x"], pos["center_y"]
            dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

            if dist < min_dist and dist < max_distance:
                min_dist = dist
                closest = emp

        return closest

    def _infer_relationships_spatial(
        self,
        employees: List[Dict],
        existing_relationships: set
    ) -> List[Tuple[str, str]]:
        """
        Infer manager-employee relationships using spatial proximity.

        Heuristic: An employee is managed by the closest box in the level above,
        within a reasonable horizontal distance (same "branch" of the tree).
        """
        relationships = []

        # Group employees by level
        levels: Dict[int, List[Dict]] = {}
        for emp in employees:
            level = emp["level"]
            if level not in levels:
                levels[level] = []
            levels[level].append(emp)

        # For each level (except the top), find managers from level above
        sorted_levels = sorted(levels.keys())

        for level_idx in range(1, len(sorted_levels)):
            current_level = sorted_levels[level_idx]
            parent_level = sorted_levels[level_idx - 1]

            employees_at_level = levels[current_level]
            potential_managers = levels[parent_level]

            for employee in employees_at_level:
                # Skip if already has a relationship
                if any(r[1] == employee["id"] for r in existing_relationships):
                    continue

                # Find closest manager horizontally within reasonable range
                closest_manager = None
                min_score = float("inf")

                for manager in potential_managers:
                    # Calculate horizontal distance between centers
                    horizontal_dist = abs(
                        employee["position"]["center_x"] -
                        manager["position"]["center_x"]
                    )

                    # Only consider managers within max horizontal distance
                    if horizontal_dist > self.max_horizontal_distance:
                        continue

                    # Score: prefer closer horizontally, slight preference for directly above
                    vertical_dist = abs(
                        employee["position"]["center_y"] -
                        manager["position"]["center_y"]
                    )
                    score = horizontal_dist + (vertical_dist * 0.1)

                    if score < min_score:
                        closest_manager = manager
                        min_score = score

                if closest_manager:
                    rel = (closest_manager["id"], employee["id"])
                    if rel not in existing_relationships:
                        relationships.append(rel)

        return relationships

    def _build_org_graph(
        self,
        employees: List[Dict],
        relationships: List[Tuple[str, str]]
    ) -> ParseResult:
        """
        Build NetworkX graph and identify forests (multiple root nodes) and orphans.
        """
        G = nx.DiGraph()

        # Add nodes
        for emp in employees:
            G.add_node(emp["id"], **emp)

        # Add edges (manager → employee)
        for manager_id, employee_id in relationships:
            if manager_id in G and employee_id in G:
                G.add_edge(manager_id, employee_id)

        # Find root nodes (no incoming edges)
        roots = [node for node in G.nodes() if G.in_degree(node) == 0]

        # Build separate trees for each root
        forests = []
        assigned_nodes = set()

        for root in roots:
            try:
                descendants = nx.descendants(G, root)
            except nx.NetworkXError:
                descendants = set()

            descendants.add(root)
            subtree_nodes = list(descendants)

            root_data = G.nodes[root]
            forests.append({
                "root_id": root,
                "root_name": root_data.get("name", "Unknown"),
                "root_title": root_data.get("title", "Unknown"),
                "node_count": len(subtree_nodes),
                "nodes": subtree_nodes,
                "max_depth": self._calculate_max_depth(G, root),
            })

            assigned_nodes.update(subtree_nodes)

        # Identify unassigned (orphaned) nodes
        all_nodes = set(G.nodes())
        unassigned_nodes = all_nodes - assigned_nodes

        unassigned = []
        for node_id in unassigned_nodes:
            node_data = G.nodes[node_id]
            unassigned.append({
                "id": node_id,
                "name": node_data.get("name", "Unknown"),
                "title": node_data.get("title", "Unknown"),
                "level": node_data.get("level", 0),
                "reason": "No path to any root node",
            })

        return ParseResult(
            employees=employees,
            relationships=list(relationships),
            forests=sorted(forests, key=lambda f: -f["node_count"]),
            unassigned=unassigned,
            metadata={},
            graph=G,
        )

    def _calculate_max_depth(self, G: nx.DiGraph, root: str) -> int:
        """Calculate maximum depth from root node."""
        try:
            lengths = nx.single_source_shortest_path_length(G, root)
            return max(lengths.values()) if lengths else 0
        except Exception:
            return 0

    def _calculate_hierarchy_depth(self, G: nx.DiGraph) -> int:
        """
        Calculate the ACTUAL hierarchy depth from the graph structure.

        This returns the true number of organizational layers based on
        the longest path from any root to any leaf node.

        Returns:
            Number of organizational layers (depth + 1)
        """
        if G is None or G.number_of_nodes() == 0:
            return 0

        # Find root nodes (nodes with no incoming edges)
        roots = [node for node in G.nodes() if G.in_degree(node) == 0]

        if not roots:
            # No clear root - might be a cycle or disconnected
            return len(set(G.nodes()))

        max_depth = 0
        for root in roots:
            try:
                # Get all path lengths from this root
                lengths = nx.single_source_shortest_path_length(G, root)
                if lengths:
                    root_max_depth = max(lengths.values())
                    max_depth = max(max_depth, root_max_depth)
            except nx.NetworkXError:
                continue

        # Return layers count (depth + 1, since depth 0 = 1 layer)
        return max_depth + 1

    def _assign_graph_based_levels(
        self,
        G: nx.DiGraph,
        employee_dicts: List[Dict]
    ) -> None:
        """
        Assign correct hierarchy levels to employees based on graph structure.

        This replaces the K-Means clustering levels with actual graph-based
        levels calculated from the distance to root nodes.

        Args:
            G: The organization graph
            employee_dicts: List of employee dictionaries to update in-place
        """
        if G is None or G.number_of_nodes() == 0:
            return

        # Find root nodes
        roots = [node for node in G.nodes() if G.in_degree(node) == 0]

        # Calculate level for each node (distance from nearest root + 1)
        node_levels = {}

        for root in roots:
            try:
                lengths = nx.single_source_shortest_path_length(G, root)
                for node_id, depth in lengths.items():
                    # Level is depth + 1 (root is level 1, not level 0)
                    level = depth + 1
                    # Use minimum level if node is reachable from multiple roots
                    if node_id not in node_levels or level < node_levels[node_id]:
                        node_levels[node_id] = level
            except nx.NetworkXError:
                continue

        # Update employee dictionaries with graph-based levels
        for emp in employee_dicts:
            emp_id = emp.get("id")
            if emp_id in node_levels:
                emp["level"] = node_levels[emp_id]
            # Also update the node in the graph
            if emp_id in G.nodes:
                G.nodes[emp_id]["level"] = emp.get("level", 1)

        logger.info(
            f"Assigned graph-based levels to {len(node_levels)} employees. "
            f"Levels: {sorted(set(node_levels.values()))}"
        )


def parse_pptx_file(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to parse a PPTX file and return results as dict.

    Args:
        file_path: Path to the .pptx file

    Returns:
        Dictionary with parsed org chart data
    """
    parser = OrgChartParser(file_path)
    result = parser.parse()
    return result.to_dict()
