from honeybee.hbsurface import HBSurface
from honeybee.hbfensurface import HBFenSurface
from honeybee.hbshadesurface import HBShadingSurface

from honeybee.radiance.properties import RadianceProperties
from honeybee.radiance.material.glass import Glass

from honeybee.surfacetype import Wall, Roof, Floor, ExposedFloor, Context,\
    UndergroundWall, UndergroundSlab, Ceiling, AirWall, UndergroundCeiling, SlabOnGrade, Context, Window


def get_surface_type(surface):
    """Return Honeybee Surface Type from gbXML Surface dict

    Arguments:
        surface {dict} -- gbXML dictionary for a surface

    Returns:
        SurfaceType -- a Honeybee Surface Type
    """

    surface_type = surface.getAttribute('surfaceType')

    gbxml_surface_types = {
        "InteriorWall": Wall(),
        "ExteriorWall": Wall(),
        "Roof": Roof(),
        "InteriorFloor": Floor(),
        "ExposedFloor": ExposedFloor(),
        "Shade": Context(),
        "UndergroundWall": UndergroundWall(),
        "UndergroundSlab": UndergroundSlab(),
        "Ceiling": Ceiling(),
        "Air": AirWall(),
        "UndergroundCeiling": UndergroundCeiling(),
        "RaisedFloor": ExposedFloor(),
        "SlabOnGrade": SlabOnGrade(),
        "FreestandingColumn": Context(),
        "EmbdeddedColumn": Context()
    }

    surface_type = gbxml_surface_types[surface_type]

    return surface_type


def get_opening_type(opening):
    """Return Honeybee Surface Type from gbXML Opening dict

    Arguments:
        opening {dict} -- gbXML dictionary for an opening

    Returns:
        SurfaceType -- a Honeybee Surface Type
    """
    opening_type = opening.getAttribute('openingType')

    gbxml_opening_types = {
        "FixedWindow": Window(),
        "OperableWindow": Window(),
        "FixedSkylight": Window(),
        "OperableSkylight": Window(),
        "SlidingDoor": Wall(),
        "NonSlidingDoor": Wall(),
        "Air": AirWall()
    }

    opening_type = gbxml_opening_types[opening_type]

    return opening_type


def get_points(surface):
    """Return ordered list of surface points from gbXML surface/opening

    Arguments:
        surface {dict} -- gbXML Surface or Opening dictionary

    Returns:
        List -- a list of (x, y, z) point coordinate tuples
    """
    planar_geo = surface.getElementsByTagName('PlanarGeometry')[0]
    pts = []
    points = planar_geo.getElementsByTagName('CartesianPoint')
    for point in points:
        x = point.getElementsByTagName('Coordinate')[0].childNodes[0].nodeValue
        y = point.getElementsByTagName('Coordinate')[1].childNodes[0].nodeValue
        z = point.getElementsByTagName('Coordinate')[2].childNodes[0].nodeValue
        pts.append((float(x), float(y), float(z)))
    return pts


def get_clean_name(surface_name):
    """Return Honeybee compatible surface name from the surface

    Arguments:
        surface_name {str} -- a gbXML surface name

    Returns:
        str -- a Honeybee compatible surface name
    """
    surface_name = surface_name.replace(' ', '_')
    surface_name = surface_name.replace(':', '_')
    surface_name = surface_name.replace('[', '_')
    surface_name = surface_name.replace(']', '_')
    return surface_name


def get_fenestration(surface):
    """Return Honeybee Fenestration objects from a gbXML surface dictionary

    Arguments:
        surface {dict} -- a gbXML Surface dictionary

    Returns:
        [] -- a list of HoneybeeFenestration Surfaces
    """
    openings = surface.getElementsByTagName('Opening')

    fenestrations = []

    for opening in openings:
        opening_name_raw = surface.getElementsByTagName(
            'Name')[0].childNodes[0].nodeValue
        opening_name = get_clean_name(opening_name_raw)
        opening_type = get_opening_type(opening)
        points = get_points(opening)

        if isinstance(opening_type, Window):
            fenestrations.append(HBFenSurface(name=opening_name,
                                              sorted_points=points,
                                              is_name_set_by_user=True))

        elif isinstance(opening_type, AirWall):
            air_glass = Glass(name='Air_Glass',
                              r_transmittance=1.0,
                              g_transmittance=1.0,
                              b_transmittance=1.0,
                              refraction_index=1.52)
            fenestrations.append(HBFenSurface(name=opening_name,
                                              sorted_points=points,
                                              is_name_set_by_user=True,
                                              rad_properties=air_glass))
    return fenestrations


def get_hb_surfaces(gbxml_surfaces):
    """Parses a list of gbXML surface objects to return two lists of honeybee surfaces
    
    Arguments:
        gbxml_surfaces {list} -- list of gbXML surfaces preparsed
    
    Returns:
        hb_surfaces {list} -- list of honeybee surfaces from the building studied with fenestration a child surfaces
        context_hb_surfaces {list} -- list of context surfaces which are not part of the project focus
    """

    hb_surfaces = []
    hb_context_surfaces = []


    for surface in gbxml_surfaces:
        # Get surface name
        surface_name_raw = surface.getElementsByTagName('Name')[0].childNodes[0].nodeValue
        surface_name = get_clean_name(surface_name_raw)
        
        # Get surface material information
        material_name = surface.getElementsByTagName('CADObjectId')[0].childNodes[0].nodeValue

        # Get surface type and return a compatible Honeybee Surface Type class
        surface_type = get_surface_type(surface)
        
        # Get all the points in the Planar Geometry Polyloop and return them as a list of (x, y, z)
        surface_points = get_points(surface)

        # Ignore AirWalls => They are not important for daylighting
        if isinstance(surface_type, AirWall):
            pass

        # Sometimes air walls are only indicated through materials...
        elif '_AIR' in material_name:
            pass
        
        # Any context surfaces are saved seperately to be added or removed depending on the use case
        elif isinstance(surface_type, Context):
            hb_surface = HBShadingSurface(name=surface_name,
                                        sorted_points=surface_points,
                                        is_name_set_by_user=True)

            hb_context_surfaces.append(hb_surface)

        # Finally we get to Honeybee Surfaces!
        else:
            hb_surface = HBSurface(name=surface_name,
                                sorted_points=surface_points,
                                surface_type=surface_type,
                                is_name_set_by_user=True)

            # This function does essentially the same task as the loop above but for glazing
            fenestrations = get_fenestration(surface)
            for fenestration in fenestrations:
                hb_surface.add_fenestration_surface(fenestration)
                
            hb_surfaces.append(hb_surface)

    return hb_surfaces, hb_context_surfaces
