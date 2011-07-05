<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:sld="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml" version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>default_dem</sld:Name>
    <sld:UserStyle>
      <sld:Name>default_dem</sld:Name>
      <sld:Title>default_dem</sld:Title>
      <sld:IsDefault>1</sld:IsDefault>
      <sld:FeatureTypeStyle>
        <sld:Name>default_dem</sld:Name>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:Geometry>
              <ogc:PropertyName>geom</ogc:PropertyName>
            </sld:Geometry>
            <sld:ColorMap>
              <ColorMapEntry color="#000000" quantity="-11000" label="values"/>
              <ColorMapEntry color="#08306D" quantity="-5000" label="values"/>              
              <ColorMapEntry color="#08306D" quantity="-1000" label="values"/>
              <ColorMapEntry color="#08306D" quantity="-100" label="values"/>              
              <ColorMapEntry color="#4292C3" quantity="-50" label="values"/>
              <ColorMapEntry color="#4292C3" quantity="-40" label="values"/>              
              <ColorMapEntry color="#9FC9DF" quantity="-30" label="values"/>
              <ColorMapEntry color="#DDEBF4" quantity="-20" label="values"/>              
              <ColorMapEntry color="#DDEBF4" quantity="-10" label="values"/>
              <ColorMapEntry color="#003300" quantity="0" label="values"/>
              <ColorMapEntry color="#333300" quantity="20" label="values"/>
              <ColorMapEntry color="#CC9900" quantity="50" label="values"/>
              <ColorMapEntry color="#996600" quantity="100" label="values"/>
              <ColorMapEntry color="#996633" quantity="150" label="values"/>
              <ColorMapEntry color="#CC6600" quantity="300" label="values"/>
              <ColorMapEntry color="#993300" quantity="800" label="values"/>
              <ColorMapEntry color="#663300" quantity="1100" label="values"/>
              <ColorMapEntry color="#663333" quantity="1800" label="values"/>
              <ColorMapEntry color="#ffffff" quantity="2500" label="values"/>
              <ColorMapEntry color="#ffffff" quantity="3000" label="values"/>
              <ColorMapEntry color="#ffffff" quantity="4000" label="values"/>
              <ColorMapEntry color="#ffffff" quantity="6000" label="values"/>
              <ColorMapEntry color="#ffffff" quantity="7000" label="values"/>
              <ColorMapEntry color="#ffffff" quantity="8000" label="values"/>
              <ColorMapEntry color="#ffffff" quantity="9000" label="values"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>