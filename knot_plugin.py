bl_info = {
    "name": "Knot generator",
    "description": """Creates 3D meshes of knots from simple ASCII art descriptions.""",
    "author": "John H. Williamson",
    "version": (0, 0, 1),
    "blender": (2, 7, 0),
    "location": "3D View > Tools",
    "warning": "", # used for warning icon and text in addons panel
    "wiki_url": "https://github.com/johnhw/blender_knots/wiki",
    "tracker_url": "https://github.com/johnhw/blender_knots/issues",
    "category": "Development"
}

### Knot parsing
from collections import defaultdict

char_dirs = {"^":(0,-1), "V":(0,1), ">":(1,0), "<":(-1,0), "O":(0,0)}
inv_dirs = {v:k for k,v in char_dirs.items()}

def nonempty(kmap, x, y):
        return [(x_off, y_off) 
                for x_off,y_off in char_dirs.values()
                if (x+x_off, y+y_off) in kmap]
    
# ^V>< move in this direction
# # invalid direction; this is an error
# U continue in current direction, but go underneath
# O stop; end of lead
# C check neighbours; must only be one neighbour not equal to current direction; take that
# L change label of lead (from the label map)
table = """
*   O ^ V > <
O   C # # # #
.   # . . . .
^   ^ ^ # U U
V   V # V U U
>   > U U > #
<   < U U # <
-   # U U > <
|   # ^ V U U
/   # > < ^ V
\   # < > V ^
+   # C C C C        
L   # L L L L
"""

# compute the table of possibilities
follow_map = {}
for line in table.splitlines():
    base_dirs = "O^V><"
    if len(line)>1:        
        chars = line.split()
        in_char,out_chars = chars[0], chars[1:]
        for i, c in enumerate(base_dirs):
            follow_map[(in_char, base_dirs[i])] = out_chars[i]
            
class KnotException(Exception):
    pass

class Knot:
    def parse_map(self, s):
        # convert from the ascii string to a dictionary of coordinates
        self.map = {}
        self.inv_map = defaultdict(list)
        self.labels = {}       
        self.crossovers = []
        self.lead_map = defaultdict(list)
        
        
        # represents a label object, that many
        # cells might refer to
        class Label:
            def __init__(self):
                self.label = ""
            def append(self, c):
                self.label += c            
                
        def mark_label(x,y):
            self.map[(x,y)] = 'L'
            self.inv_map['L'].append((x,y))
            self.labels[(x,y)] = label
                
        for y, line in enumerate(s.splitlines()):
            mark_invalid = False # clear invalid area flag
            for x, char in enumerate(line):
                
                if not mark_invalid:
                    # label 
                    if char=='[':
                        mark_invalid = True
                        label = Label()   # new label object                     
                        mark_label(x,y)                        
                    elif not char.isspace():
                        self.map[(x,y)] = char
                        self.inv_map[char].append((x,y))
                else:                    
                    if char==']':
                        # label finished; record it
                        mark_invalid = False
                        #self.labels[label_start] = line[label_start[0]+1:x]                    
                        mark_label(x,y)
                    else:
                        # mark these parts of the map as invalid
                        mark_label(x,y)
                        # and append to the label (reading left-to-right)
                        label.append(char)
                        
                    
                        
    def choose(self, x, y, dx, dy):
        """Return the neighbouring point that is going in a different direction,
        or throw an error if there is none or more than one."""
        neighbours = nonempty(self.map, x, y)        
        valid = [(vx, vy) for vx,vy in neighbours if not(vx==-dx and vy==-dy) and not(vx==0 and vy==0)]  
        
        if len(valid)<1:
            self.raise_error(x,y, "No neighbour to turn to")              
        if len(valid)>1:
            self.raise_error(x,y,"Ambiguous neighbour")            
        return valid[0]
    
    def find_heads(self):
        """Find each starting head"""                    
        heads = []
        
        # add in digit characters
        head_dirs = dict(char_dirs)
        head_dirs.update({str(d):(0,0) for d in range(10)})
        
        
        # find all potential heads
        for char, (x_off,y_off) in head_dirs.items():
            locations = self.inv_map[char]
            for x,y in locations:                                
                if x_off==0 and y_off==0:
                    # undirected head
                    x_off, y_off = self.choose(x,y,0,0)
                    if char.isdigit():
                        # named head
                        heads.append((x,y,x_off,y_off,0,char))
                    else:
                        heads.append((x,y,x_off,y_off,0,""))
                else:
                    # check if this is a head (no space beforehand)
                    prev_lead = self.map.get((x-x_off, y-y_off), None)                        
                    if prev_lead is None:                        
                        heads.append((x,y,x_off,y_off,0,""))
                        
        # sort by y then x
        return sorted(heads, key=lambda x:(x[1], x[0]))
        
    def print_error(self, x, y, msg=""):
        """Print out a message with an error about the knot being parsed"""
        k = 3
        n = 6
        print(msg.center(n*2))
        for i in range(-n,n+1):
            for j in range(-n, n+1):
                if (abs(j)==k and abs(i)<k) or (abs(j)<k and abs(i)==k):
                    print("@", end="")
                else:
                    char = self.map.get((x+j,y+i))
                    char = char or " "
                    print(char, end="")
            print()
        raise KnotException(msg)
        
    def raise_error(self, x, y, msg=""):
        """Print out a message with an error about the knot being parsed"""
        k = 3
        n = 6
        str = [msg.center(n*2)]
        
        for i in range(-n,n+1):
            for j in range(-n, n+1):
                if (abs(j)==k and abs(i)<k) or (abs(j)<k and abs(i)==k):
                    str.append("@")
                    
                else:
                    char = self.map.get((x+j,y+i))
                    char = char or " "
                    str.append(char)
                    
            str.append("\n")
        raise KnotException("".join(str))
    
    def print_map(self, kmap):      
        """Print out the entire map, in canonical form."""
        def vrange(ix):
            vs = [pt[ix] for pt in kmap.keys()]
            return min(vs), max(vs)
        min_x, max_x = vrange(0)
        min_y, max_y = vrange(1)
        for i in range(min_y, max_y+1):
            for j in range(min_x, max_x+1):
                char = kmap.get((j,i))
                char = char or " "
                print(char, end="")
            print()
                
                                
    
    def trace_leads(self):
        heads = self.find_heads()        
        
        self.leads = []
        self.over_map = defaultdict(list)
        ix = 0
        # trace each lead, starting from each head found
        for head in heads:
            lead = []
            x,y,dx,dy,z,name = head
                 
            lead.append((x,y,dx,dy,z,name))
            x,y = x+dx, y+dy
            while (x,y) in self.map:                
                char = self.map.get((x,y))                
                # where we are going now (as a character)
                dir_char = inv_dirs[(dx,dy)]
                
                action = follow_map.get((char, dir_char))
                # simple change of direction
                if action in char_dirs:
                    dx, dy = char_dirs[action]
                    z = 0
                elif action=='L':
                    # rename lead
                    name = self.labels[(x,y)].label
                elif action=='U':
                    # dx,dy don't change
                    z = -1
                    self.crossovers.append((x,y))
                    
                elif action=='C':
                    dx, dy = self.choose(x,y,dx,dy)
                    z = 0
                elif action=='.':
                    break
                elif action=='#':
                    self.raise_error(x,y, "Invalid direction") 
                elif action is None:
                    self.raise_error(x,y,"Character %s unexpected"%char)
                    
                lead.append((x,y,dx,dy,z,name))
                self.over_map[(x,y)].append((ix, dx, dy, z))
                # record where we are in the lead map
                self.lead_map[(x,y)].append((lead, ix))
                ix += 1
                x, y = x+dx, y+dy
            self.leads.append(lead)
               
            
    def show_lead(self, lead):
        kmap = {}
        for x,y,dx,dy,z,name in lead:
            if dx==0 and (x,y) not in kmap:
                kmap[(x,y)] = '|'
            elif  (x,y) not in kmap:
                kmap[(x,y)] = '-'
            elif (x,y) in kmap:
                kmap[(x,y)] = '+'            
                        
        self.raise_map(kmap)
        
    def show_lead_directed(self, lead):
        kmap = {}
        for x,y,dx,dy,z,name in lead:
            char = inv_dirs[(dx,dy)]
            kmap[(x,y)] = char
                        
        self.print_map(kmap)
        
    def show_all_leads_directed(self):
        kmap = {}
        for lead in self.leads:
            for x,y,dx,dy,z,name in lead:
                char = inv_dirs[(dx,dy)]
                kmap[(x,y)] = char
                            
        self.print_map(kmap)
        
    def __init__(self, s):
        """Take a string representation of a knot, and fill 
        in the knot data from the string."""
        # generate map of characters
        self.parse_map(s)
        self.trace_leads()
        
        
               
    def is_crossing(self, x, y):
        print((x,y))
        cross = self.over_map.get((x,y))
        return cross is not None and len(cross)>1
    
       
        
        
### END knot parsing

### Blender Python interface
import bpy

from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       EnumProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Operator,
                       PropertyGroup,
                       )





class KnotSettings(PropertyGroup):
    
    knot_text = StringProperty(
        name="Knot",
        description="Select knot to choose",
        default = ""
        )
    scale = FloatProperty(
        name="Scale",
        description="Scaling of knot",
        default = 0.3,
        min=0.0,
        max=5.0
        )

    extrude = BoolProperty(
        name="Extrude",
        description="Extrude knot; otherwise no bevel is applied to the curve",
        default = True
        )
        
    extrude_width = FloatProperty(
        name="Width",
        description="Extrusion (bevel) width",
        default = 0.3,
        min=0.0,
        max=10.0
        )

    curve = BoolProperty(
        name="Create Curve",
        description="Create curve (otherwise, create a plain mesh)",
        default=True)
        
    smoothing = IntProperty(
        name = "Smoothing steps",
        description="Number of smoothing steps to apply after knot generated",
        default = 5,
        min = 0,
        max = 30
        )
        
    subdiv = IntProperty(
        name = "Subdivision",
        description="Number of subdivisions to apply",
        default = 5,
        min = 0,
        max = 30
        )

    z_depth = FloatProperty(
        name = "Depth",
        description="Z shift at crossovers",
        default = 1,
        min = 0,
        max = 10
        )
        
    z_bias = FloatProperty(
        name = "Bias",
        description="Z bias at crossovers (-1=over rises, 0=split, 1=under lowers)",
        default = 0,
        min = -1,
        max = 1
        )
        
    





import bpy
from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector
    
def add_knot(self, context, knot_string, z_scale, bias, scale, name="Knot"):
    
    ix = 0
    verts = []
    edges = []
    
    knot_obj = Knot(knot_string)
    
    # must have at least on lead for this to work
    if len(knot_obj.leads)<1:
        raise KnotException("Warning: no valid knot found")        
    
    for lead in knot_obj.leads:
        prev = None
        for x,y,dx,dy,z,name in lead:
            if knot_obj.is_crossing(x,y):
                if z==-1:
                    verts.append(Vector((x,-y,-z_scale * (bias+1)/2)))
                else:
                    verts.append(Vector((x,-y,z_scale*  (bias+1)/2)))                    
            else:
                verts.append(Vector((x,-y,0)))
                
            if prev is not None:
                edges.append((prev, ix))
            prev = ix
            ix += 1
                            
    mesh = bpy.data.meshes.new(name=name)
    mesh.from_pydata(verts, edges, [])    
    mesh.validate(verbose=True)
    object_data_add(context, mesh, operator=self)
    
    
class KnotOperator(bpy.types.Operator,AddObjectHelper):
    bl_idname = "wm.make_knot"
    bl_label = "Make Knot"

    def execute(self, context):
        scene = context.scene
        knottool = scene.knot_tool
        knot = bpy.data.texts[knottool.knot_text].as_string()
                
        try:
            add_knot(self, context, knot, knottool.z_depth, knottool.z_bias, knottool.scale, knottool.knot_text)
        except KnotException as ke:
            print(str(ke))
            self.report({'ERROR'}, str(ke))
            return {"CANCELLED"}
            
        # convert mesh to curve
        if knottool.curve:
            bpy.ops.object.convert(target="CURVE")

            active = bpy.context.object
            curves = active.data
            
            # apply beveling
            curves.fill_mode = 'FULL'
            curves.bevel_depth = knottool.extrude_width       
            curves.bevel_resolution = 6
            curves.use_uv_as_generated = True
        
        # add smooth modifier
        if knottool.smoothing>0:
            bpy.ops.object.modifier_add(type="SMOOTH")
            active.modifiers['Smooth'].iterations = knottool.smoothing        
            
        # add subdivision surface modifier
        if knottool.subdiv>0:
            bpy.ops.object.modifier_add(type="SUBSURF")
            active.modifiers['Subsurf'].levels = knottool.subdiv
            active.modifiers['Subsurf'].render_levels = knottool.subdiv
            

        # recenter the cursor to the origin of the knot (mean position)
        saved_location = bpy.context.scene.cursor_location.copy()  # returns a copy of the vector    
        bpy.ops.object.mode_set(mode = 'EDIT')    
        if knottool.curve:
            bpy.ops.curve.select_all(action='SELECT')        
        else:
            bpy.ops.mesh.select_all(action='SELECT')        
        bpy.ops.view3d.snap_cursor_to_selected()
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        # set the origin on the current object to the 3dcursor location
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        # set 3dcursor location back to the stored location
        bpy.context.scene.cursor_location = saved_location
        bpy.ops.object.location_clear()
        bpy.ops.object.rotation_clear()
        bpy.ops.object.scale_clear()
        bpy.ops.transform.resize(value=(knottool.scale, knottool.scale, knottool.scale))

        return {'FINISHED'}



class OBJECT_PT_my_panel(Panel):
    bl_idname = "OBJECT_PT_knot"
    bl_label = "Knot"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"    
    bl_category = "Create"
    bl_context = "objectmode"   

    @classmethod
    def poll(self,context):
        return True

    def draw(self, context):
        # Draw the UI panel
        layout = self.layout
        scene = context.scene
        myknot = scene.knot_tool

        layout.prop_search(context.scene.knot_tool, 'knot_text', bpy.data, 'texts', text="Knot")               
        layout.prop(myknot, "scale")
        

        layout.prop(myknot, "extrude")
        
        # extrusion box
        box = layout.box()
        box.label("Extrude")
        
        box.prop(myknot, "extrude_width")
        box.prop(myknot, "smoothing")
        box.prop(myknot, "subdiv")
        box.enabled = myknot.extrude
            
            
        # z shift box
        box = layout.box()
        box.label("Over/Under Z shift")
        box.prop(myknot, "z_depth")
        box.prop(myknot, "z_bias")

        
        # Create knot button
        layout.operator("wm.make_knot")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.knot_tool = PointerProperty(type=KnotSettings)



def unregister():
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.knot_tool

if __name__ == "__main__":
    register()