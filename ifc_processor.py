import os
import statistics
import ifcopenshell
import ifcopenshell.geom
import matplotlib.pyplot as plt


def clip_triangle_with_plane(p0, p1, p2, y_plane, epsilon=1e-4):
    """Robustes Polygon-Clipping für saubere Schnitte, fängt auch flache Wände ab."""
    pts = [p0, p1, p2]
    d = [p[1] - y_plane for p in pts]
    
    if all(abs(di) < epsilon for di in d):
        return [
            ((pts[0][0], pts[0][2]), (pts[1][0], pts[1][2])),
            ((pts[1][0], pts[1][2]), (pts[2][0], pts[2][2])),
            ((pts[2][0], pts[2][2]), (pts[0][0], pts[0][2]))
        ]
        
    if all(di > epsilon for di in d) or all(di < -epsilon for di in d):
        return []
        
    intersections = []
    for i in range(3):
        p_a, p_b = pts[i], pts[(i + 1) % 3]
        d_a, d_b = d[i], d[(i + 1) % 3]
        
        if (d_a > epsilon and d_b < -epsilon) or (d_a < -epsilon and d_b > epsilon):
            t = d_a / (d_a - d_b)
            ix = p_a[0] + t * (p_b[0] - p_a[0])
            iz = p_a[2] + t * (p_b[2] - p_a[2])
            intersections.append((ix, iz))
        elif abs(d_a) <= epsilon:
            intersections.append((p_a[0], p_a[2]))
    
    unique = []
    for pt in intersections:
        if not any(abs(pt[0]-u[0]) < epsilon and abs(pt[1]-u[1]) < epsilon for u in unique):
            unique.append(pt)
            
    if len(unique) == 2:
        return [(unique[0], unique[1])]
    return []

def is_external_wall(wall):
    """Prüft über IFC-Metadaten, ob eine Wand eine Außenwand ist (Fix B)."""
    for rel in getattr(wall, "IsDefinedBy", []):
        prop_set = getattr(rel, "RelatingPropertyDefinition", None)
        if prop_set and prop_set.is_a("IfcPropertySet") and getattr(prop_set, "Name", "") == "Pset_WallCommon":
            for prop in getattr(prop_set, "HasProperties", []):
                if getattr(prop, "Name", "") == "IsExternal" and prop.is_a("IfcPropertySingleValue"):
                    val = getattr(prop, "NominalValue", None)
                    if val is not None:
                        return bool(val.wrappedValue)
    return None 

class IfcProcessor:
    def __init__(self, file_path: str):
        """Initialisiert den Prozessor und lädt die IFC-Datei in den Speicher."""
        self.ifc_file = ifcopenshell.open(file_path)

    def _is_external_element(self, element: Any) -> bool:
        """
        Hilfsfunktion: Prüft in den IFC-Metadaten, ob ein Element eine Außenwand ist.
        Gibt standardmäßig True zurück, wenn die Eigenschaft nicht gefunden wird,
        um auf der sicheren Seite zu sein und keine Fassadenteile zu verlieren.
        """

        if hasattr(element, 'IsDefinedBy'):
            for definition in element.IsDefinedBy:
                # Wir suchen nach Eigenschafts-Definitionen
                if definition.is_a('IfcRelDefinesByProperties'):
                    prop_set = definition.RelatingPropertyDefinition
                    # Wir suchen gezielt das Standard-Set für Wände
                    if prop_set.is_a('IfcPropertySet') and prop_set.Name == 'Pset_WallCommon':
                        for prop in prop_set.HasProperties:
                            # Wir lesen den Wert für 'IsExternal' aus
                            if prop.Name == 'IsExternal':
                                return bool(prop.NominalValue.wrappedValue)
        
        
        return True

    def get_storeys(self) -> List[Dict[str, Any]]:
        """Extrahiert alle Geschosse und sortiert sie nach ihrer vertikalen Z-Höhe."""
        storeys = self.ifc_file.by_type("IfcBuildingStorey")
        storey_data = []
        for storey in storeys:
            elevation = storey.Elevation if hasattr(storey, 'Elevation') and storey.Elevation is not None else 0.0
            name = storey.Name if hasattr(storey, 'Name') and storey.Name else "Unbenannt"
            storey_data.append({"name": name, "elevation": elevation, "element": storey})
        
        return sorted(storey_data, key=lambda x: x["elevation"])

    def generate_floor_plans(self, storeys: List[Dict[str, Any]], base_name: str = "Haus", output_dir: str = "output", z_tolerance: float = 1.5):
        """Generiert SVG-Grundrisse für jedes Geschoss."""
        print(f"\n--- Generiere Grundrisse (SVG) für {base_name} ---")
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
        
        elements = (self.ifc_file.by_type("IfcWall") + 
                   self.ifc_file.by_type("IfcWallStandardCase") +
                   self.ifc_file.by_type("IfcDoor") + 
                   self.ifc_file.by_type("IfcWindow"))
                   
        if not elements: 
            return

        for storey in storeys:
            storey_name = storey["name"]
            z_level = storey["elevation"]
            
            fig, ax = plt.subplots(figsize=(12, 12))
            ax.set_aspect('equal')
            ax.set_title(f"Grundriss - {base_name} - {storey_name}", fontsize=14, fontfamily='sans-serif')
            ax.axis('off')
            
            elements_drawn = 0
            for elem in elements:
                try:
                    shape = ifcopenshell.geom.create_shape(settings, elem)
                    verts = shape.geometry.verts
                    edges = shape.geometry.edges
                    
                    if len(verts) >= 3:
                        z_coords = [verts[i] for i in range(2, len(verts), 3)]
                        # Magic Number entfernt: Wir nutzen jetzt die Variable z_tolerance
                        if abs(min(z_coords) - z_level) < z_tolerance:
                            for i in range(0, len(edges), 2):
                                v1_idx, v2_idx = edges[i], edges[i+1]
                                x1, y1 = verts[v1_idx*3], verts[v1_idx*3 + 1]
                                x2, y2 = verts[v2_idx*3], verts[v2_idx*3 + 1]
                                
                                # Hauchdünne, präzise Architekturlinien für Vektorexport
                                ax.plot([x1, x2], [y1, y2], color='#2c3e50', linewidth=0.3, alpha=0.8)
                            elements_drawn += 1
                except Exception:
                    pass
            
            if elements_drawn > 0:
                safe_name = storey_name.replace(' ', '_').replace('/', '_')
                # Dateiendung auf .svg geändert
                output_path = os.path.join(output_dir, f"{base_name}_Grundriss_{safe_name}.svg")
                plt.savefig(output_path, format='svg', bbox_inches='tight', facecolor='white')
                print(f" -> Gespeichert: {output_path}")
            plt.close(fig)

    def generate_section(self, base_name: str = "Haus", output_dir: str = "output"):
        
        print(f"--- Generiere vertikalen Schnitt für {base_name} ---")
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)

        elements = (self.ifc_file.by_type("IfcWall") + 
                    self.ifc_file.by_type("IfcWallStandardCase") + 
                    self.ifc_file.by_type("IfcSlab") + 
                    self.ifc_file.by_type("IfcRoof") +
                    self.ifc_file.by_type("IfcWindow") + 
                    self.ifc_file.by_type("IfcDoor"))

        element_shapes = []
        y_centers = []

        # Geometrie erzeugen und Y-Mittelpunkte für die exakte Gebäude-Mitte sammeln
        for elem in elements:
            try:
                shape = ifcopenshell.geom.create_shape(settings, elem)
                verts = shape.geometry.verts
                y_coords = [verts[i*3 + 1] for i in range(len(verts)//3)]
                
                if y_coords:
                    y_centers.append((min(y_coords) + max(y_coords)) / 2.0)
                    element_shapes.append(shape)
            except Exception:
                pass

        if not element_shapes:
            return

        # Median für Schnitt durch Gebäudemitte 
        y_mid = statistics.median(y_centers)

        fig, ax = plt.subplots(figsize=(12, 8))
        ax.set_aspect('equal')
        ax.set_title(f"Vertikaler Schnitt (Mitte) - {base_name}", fontsize=14, fontfamily='sans-serif')
        ax.axis('off')

        elements_drawn = 0

        for shape in element_shapes:
            verts = shape.geometry.verts
            faces = shape.geometry.faces

            for i in range(0, len(faces), 3):
                i0, i1, i2 = faces[i], faces[i+1], faces[i+2]
                p0 = (verts[i0*3], verts[i0*3+1], verts[i0*3+2])
                p1 = (verts[i1*3], verts[i1*3+1], verts[i1*3+2])
                p2 = (verts[i2*3], verts[i2*3+1], verts[i2*3+2])

                segments = clip_triangle_with_plane(p0, p1, p2, y_mid)
                for (x1, z1), (x2, z2) in segments:
                    ax.plot([x1, x2], [z1, z2], color='#2c3e50', linewidth=0.8)
                    elements_drawn += 1

        if elements_drawn > 0:
            output_path = os.path.join(output_dir, f"{base_name}_Schnitt.svg")
            plt.savefig(output_path, format='svg', bbox_inches='tight', facecolor='white')
            print(f" -> Gespeichert: {output_path}")
        plt.close(fig)

    def generate_elevation(self, base_name: str = "Haus", output_dir: str = "output"):
       
        print(f"--- Generiere Außenansicht (Front) für {base_name} ---")
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)

        # 1. Hier werden Elemente (Türen, Fenster, Wände) gesammelt, die eventl. zur Fassade gehören könnten
        all_walls = self.ifc_file.by_type("IfcWall") + self.ifc_file.by_type("IfcWallStandardCase")
        exterior_walls = [w for w in all_walls if is_external_wall(w) is not False]
        front_elements = exterior_walls + self.ifc_file.by_type("IfcWindow") + self.ifc_file.by_type("IfcDoor")

        # 2. Hier werden Dächer gesammelt, damit sie später immer mitgezeichnet werden (auch wenn sie vielleicht nicht als "Roof" klassifiziert sind)
        roof_shapes = []
        for elem in self.ifc_file.by_type("IfcRoof"):
            try:
                roof_shapes.append((elem, ifcopenshell.geom.create_shape(settings, elem)))
            except Exception: pass

        for slab in self.ifc_file.by_type("IfcSlab"):
            is_roof = False
            if getattr(slab, "PredefinedType", None) == "ROOF":
                is_roof = True
            else:
                try:
                    shape = ifcopenshell.geom.create_shape(settings, slab)
                    verts = shape.geometry.verts
                    z_coords = [verts[i*3 + 2] for i in range(len(verts)//3)]
                    if max(z_coords) - min(z_coords) > 0.8:
                        is_roof = True
                except Exception: pass

            if is_roof:
                try:
                    roof_shapes.append((slab, ifcopenshell.geom.create_shape(settings, slab)))
                except Exception: pass

        # 3. Y-Mittelpunkte werden hier für das culling gesammelt
        shapes_with_y = []
        for elem in front_elements:
            try:
                shape = ifcopenshell.geom.create_shape(settings, elem)
                verts = shape.geometry.verts
                y_coords = [verts[i*3 + 1] for i in range(len(verts)//3)]
                if y_coords:
                    y_center = (min(y_coords) + max(y_coords)) / 2.0
                    shapes_with_y.append((elem, shape, y_center))
            except Exception: pass

        # 4. Median-Filter für das Abschneiden von Elementen, die zu weit hinten liegen
        front_shapes = []
        if shapes_with_y:
            y_centers = [y for (_, _, y) in shapes_with_y]
            y_threshold = statistics.median(y_centers)
            for elem, shape, y_center in shapes_with_y:
                if y_center <= y_threshold:
                    front_shapes.append((elem, shape))

        all_shapes_to_draw = front_shapes + roof_shapes

        # 5. Hier wir das Face-by-Face Rendering vorbereitet, damit die weiße Deckschicht immer genau hinter den schwarzen Kanten liegt
        renderables = []
        for elem, shape in all_shapes_to_draw:
            verts = shape.geometry.verts
            faces = shape.geometry.faces
            edges = shape.geometry.edges
            is_wall = "Wall" in elem.is_a()
            lw = 0.5 if is_wall else 0.2

            # Weiße Deckschicht als Dreiecke, damit sie immer genau hinter den schwarzen Kanten liegt
            for i in range(0, len(faces), 3):
                i0, i1, i2 = faces[i], faces[i+1], faces[i+2]
                v0_y, v1_y, v2_y = verts[i0*3+1], verts[i1*3+1], verts[i2*3+1]
                y_avg = (v0_y + v1_y + v2_y) / 3.0
                
                xc = [verts[i0*3], verts[i1*3], verts[i2*3]]
                zc = [verts[i0*3+2], verts[i1*3+2], verts[i2*3+2]]
                
                renderables.append({
                    'type': 'face',
                    'y': y_avg,
                    'xc': xc,
                    'zc': zc
                })

            # Schwarze Kanten
            for i in range(0, len(edges), 2):
                v1_idx, v2_idx = edges[i], edges[i+1]
                v1_y, v2_y = verts[v1_idx*3+1], verts[v2_idx*3+1]
                y_avg = (v1_y + v2_y) / 2.0
                
                # Z-BIAS: Linien minimal nach vorne ziehen (-0.001), 
                # damit sie nicht von der eigenen weißen Wand verdeckt werden.
                xc = [verts[v1_idx*3], verts[v2_idx*3]]
                zc = [verts[v1_idx*3+2], verts[v2_idx*3+2]]
                
                renderables.append({
                    'type': 'edge',
                    'y': y_avg - 0.001,
                    'xc': xc,
                    'zc': zc,
                    'lw': lw
                })

        renderables.sort(key=lambda item: item['y'], reverse=True)

        # 6. Canvas wird gerendert
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.set_aspect('equal')
        ax.set_title(f"Außenansicht (Front) - {base_name}", fontsize=14, fontfamily='sans-serif')
        ax.axis('off')

        elements_drawn = 0
        current_zorder = 10  # Startwert 

        for r in renderables:
            if r['type'] == 'face':

                ax.fill(r['xc'], r['zc'], color='white', edgecolor='none', zorder=current_zorder)
            else:
                # NEU: zorder zwingt matplotlib, die Linie genau hier hinzulegen!
                ax.plot(r['xc'], r['zc'], color='#2c3e50', linewidth=r['lw'], zorder=current_zorder)
            
            current_zorder += 1
            if r['type'] == 'edge':
                elements_drawn += 1

        if elements_drawn > 0:
            output_path = os.path.join(output_dir, f"{base_name}_Ansicht.svg")
            plt.savefig(output_path, format='svg', bbox_inches='tight', facecolor='white')
            print(f" -> Gespeichert: {output_path}")
            
        plt.close(fig)