<?xml version="1.0" encoding="ISO-8859-1"?>
<StyledLayerDescriptor version="1.0.0" 
xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd" 
xmlns="http://www.opengis.net/sld" 
xmlns:ogc="http://www.opengis.net/ogc" 
xmlns:xlink="http://www.w3.org/1999/xlink" 
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                
<NamedLayer>
<Name>tsudat_subfault_contribution</Name>
<UserStyle>
<Title>TsuDAT SubFault Contribution Style</Title>
<Abstract>Style for layer tsudat_hazardpoint_rp</Abstract>
<FeatureTypeStyle>

<Rule> 
<Name>tsudat_subfault_contribution</Name>
<Title>Contribution 0</Title>
<Abstract>tsudat_subfault_contribution</Abstract>
<ogc:Filter>
         <ogc:And>
           <ogc:PropertyIsEqualTo>
             <ogc:PropertyName>contribution</ogc:PropertyName>
             <ogc:Literal>0</ogc:Literal>
           </ogc:PropertyIsEqualTo>
         </ogc:And>
  </ogc:Filter>
         <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#FFFFB2</CssParameter>
                </Fill>
              </Mark>
              <Size>2.5</Size>
            </Graphic>
          </PointSymbolizer>
</Rule>
    
<Rule> 
<Name>tsudat_subfault_contribution</Name>
<Title>Contribution 0-0.5</Title>
<Abstract>tsudat_subfault_contribution</Abstract>
<ogc:Filter>
         <ogc:And>
           <ogc:PropertyIsGreaterThan>
             <ogc:PropertyName>contribution</ogc:PropertyName>
             <ogc:Literal>0</ogc:Literal>
           </ogc:PropertyIsGreaterThan>
           <ogc:PropertyIsLessThan>
             <ogc:PropertyName>contribution</ogc:PropertyName>
             <ogc:Literal>0.5</ogc:Literal>
           </ogc:PropertyIsLessThan>
         </ogc:And>
  </ogc:Filter>
         <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#FED976</CssParameter>
                </Fill>
              </Mark>
              <Size>4</Size>
            </Graphic>
          </PointSymbolizer>
</Rule>
                
<Rule> 
<Name>tsudat_subfault_contribution</Name>
<Title>Contribution 0.5-1.0</Title>
<Abstract>tsudat_subfault_contribution</Abstract>
<ogc:Filter>
         <ogc:And>
           <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>contribution</ogc:PropertyName>
             <ogc:Literal>0.5</ogc:Literal>
           </ogc:PropertyIsGreaterThanOrEqualTo>
           <ogc:PropertyIsLessThan>
             <ogc:PropertyName>contribution</ogc:PropertyName>
             <ogc:Literal>1</ogc:Literal>
           </ogc:PropertyIsLessThan>
         </ogc:And>
  </ogc:Filter>
         <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#FEB24C</CssParameter>
                </Fill>
              </Mark>
              <Size>4</Size>
            </Graphic>
          </PointSymbolizer>
</Rule>

  <Rule> 
<Name>tsudat_subfault_contribution</Name>
<Title>Contribution 1.0-1.5</Title>
<Abstract>tsudat_subfault_contribution</Abstract>
<ogc:Filter>
         <ogc:And>
           <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>contribution</ogc:PropertyName>
             <ogc:Literal>1</ogc:Literal>
           </ogc:PropertyIsGreaterThanOrEqualTo>
           <ogc:PropertyIsLessThan>
             <ogc:PropertyName>contribution</ogc:PropertyName>
             <ogc:Literal>1.5</ogc:Literal>
           </ogc:PropertyIsLessThan>
         </ogc:And>
  </ogc:Filter>
         <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#FD8D3C</CssParameter>
                </Fill>
              </Mark>
              <Size>4</Size>
            </Graphic>
          </PointSymbolizer>
</Rule>
    <Rule> 
<Name>tsudat_subfault_contribution</Name>
<Title>Contribution 1.5-2.0</Title>
<Abstract>tsudat_subfault_contribution</Abstract>
<ogc:Filter>
         <ogc:And>
           <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>contribution</ogc:PropertyName>
             <ogc:Literal>1.5</ogc:Literal>
           </ogc:PropertyIsGreaterThanOrEqualTo>
           <ogc:PropertyIsLessThan>
             <ogc:PropertyName>contribution</ogc:PropertyName>
             <ogc:Literal>2</ogc:Literal>
           </ogc:PropertyIsLessThan>
         </ogc:And>
  </ogc:Filter>
         <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#F03B20</CssParameter>
                </Fill>
              </Mark>
              <Size>6</Size>
            </Graphic>
          </PointSymbolizer>
</Rule>
    <Rule> 
<Name>tsudat_subfault_contribution</Name>
<Title>Contribution 2.0-100</Title>
<Abstract>tsudat_subfault_contribution</Abstract>
<ogc:Filter>
         <ogc:And>
           <ogc:PropertyIsGreaterThanOrEqualTo>
             <ogc:PropertyName>contribution</ogc:PropertyName>
             <ogc:Literal>2</ogc:Literal>
           </ogc:PropertyIsGreaterThanOrEqualTo>
           <ogc:PropertyIsLessThan>
             <ogc:PropertyName>contribution</ogc:PropertyName>
             <ogc:Literal>100</ogc:Literal>
           </ogc:PropertyIsLessThan>
         </ogc:And>
  </ogc:Filter>
         <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#BD0026</CssParameter>
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