<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:sld="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:gml="http://www.opengis.net/gml" version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>flow_stage</sld:Name>
    <sld:UserStyle>
      <sld:Name>flow_stage</sld:Name>
      <sld:Title>tsunami_flow_stage</sld:Title>
      <sld:IsDefault>1</sld:IsDefault>
      <sld:FeatureTypeStyle>
        <sld:Name>name</sld:Name>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:Geometry>
              <ogc:PropertyName>geom</ogc:PropertyName>
            </sld:Geometry>
            <sld:ColorMap>
              <sld:ColorMapEntry color="#000000" opacity="0" quantity="0"/>
              <sld:ColorMapEntry color="#2E46FF" opacity="1" quantity="0.2"/>
              <sld:ColorMapEntry color="#3874FF" opacity="1" quantity="0.4"/>
              <sld:ColorMapEntry color="#38A9FF" opacity="1" quantity="0.6"/>
              <sld:ColorMapEntry color="#29DBFF" opacity="1" quantity="0.8"/>
              <sld:ColorMapEntry color="#40FFEF" opacity="1" quantity="1.0"/>
              <sld:ColorMapEntry color="#8AFFBE" opacity="1" quantity="1.2"/>
              <sld:ColorMapEntry color="#B6FF8F" opacity="1" quantity="1.4"/>
              <sld:ColorMapEntry color="#DAFF61" opacity="1" quantity="1.6"/>
              <sld:ColorMapEntry color="#F8FF26" opacity="1" quantity="1.8"/>
              <sld:ColorMapEntry color="#FFE100" opacity="1" quantity="2.0"/>
              <sld:ColorMapEntry color="#FFB300" opacity="1" quantity="3.0"/>
              <sld:ColorMapEntry color="#FF8400" opacity="1" quantity="4.0"/>
              <sld:ColorMapEntry color="#FF5100" opacity="1" quantity="5.0"/>
              <sld:ColorMapEntry color="#F70000" opacity="1" quantity="10.0"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>
