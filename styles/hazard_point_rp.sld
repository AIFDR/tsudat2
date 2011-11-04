<?xml version="1.0" encoding="ISO-8859-1"?>
<StyledLayerDescriptor version="1.0.0" 
xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd" 
xmlns="http://www.opengis.net/sld" 
xmlns:ogc="http://www.opengis.net/ogc" 
xmlns:xlink="http://www.w3.org/1999/xlink" 
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                
<NamedLayer>
<Name>tsudat_hazardpoint_rp</Name>
<UserStyle>
<Title>TsuDAT Hazard Point for Return Period Style</Title>
<Abstract>Style for layer tsudat_hazardpoint_rp</Abstract>
<FeatureTypeStyle>
              
<Rule> 
<Name>tsudat_hazardpoint_rp</Name>
<Title>Wave Height 0-3</Title>
<Abstract>tsudat_hazardpoint_rp</Abstract>
<ogc:Filter>
         <ogc:And>
           <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>wave_height</ogc:PropertyName>
             <ogc:Literal>0</ogc:Literal>
           </ogc:PropertyIsGreaterThanOrEqualTo>
           <ogc:PropertyIsLessThan>
             <ogc:PropertyName>wave_height</ogc:PropertyName>
             <ogc:Literal>3</ogc:Literal>
           </ogc:PropertyIsLessThan>
         </ogc:And>
  </ogc:Filter>
         <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#0000ff</CssParameter>
                </Fill>
              </Mark>
              <Size>2</Size>
            </Graphic>
          </PointSymbolizer>
</Rule>
  
<Rule> 
<Name>tsudat_hazardpoint_rp</Name>
<Title>Wave Height 3-6</Title>
<Abstract>tsudat_hazardpoint_rp</Abstract>
<ogc:Filter>
         <ogc:And>
           <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>wave_height</ogc:PropertyName>
             <ogc:Literal>3</ogc:Literal>
           </ogc:PropertyIsGreaterThanOrEqualTo>
           <ogc:PropertyIsLessThan>
             <ogc:PropertyName>wave_height</ogc:PropertyName>
             <ogc:Literal>6</ogc:Literal>
           </ogc:PropertyIsLessThan>
         </ogc:And>
  </ogc:Filter>
         <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#00ff00</CssParameter>
                </Fill>
              </Mark>
              <Size>4</Size>
            </Graphic>
          </PointSymbolizer>
</Rule>

  <Rule> 
<Name>tsudat_hazardpoint_rp</Name>
<Title>Wave Height 6-10</Title>
<Abstract>tsudat_hazardpoint_rp</Abstract>
<ogc:Filter>
         <ogc:And>
           <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>wave_height</ogc:PropertyName>
             <ogc:Literal>6</ogc:Literal>
           </ogc:PropertyIsGreaterThanOrEqualTo>
           <ogc:PropertyIsLessThan>
             <ogc:PropertyName>wave_height</ogc:PropertyName>
             <ogc:Literal>10</ogc:Literal>
           </ogc:PropertyIsLessThan>
         </ogc:And>
  </ogc:Filter>
         <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#ff0000</CssParameter>
                </Fill>
              </Mark>
              <Size>6</Size>
            </Graphic>
          </PointSymbolizer>
</Rule>
</FeatureTypeStyle>
</UserStyle>
</NamedLayer>
</StyledLayerDescriptor>