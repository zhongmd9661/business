"""测试 XML 发票转 Markdown"""
import tempfile
from pathlib import Path

from src.batch_processing.xml_to_md import xml_to_markdown


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<root>
  <Header>
    <InherentLabel>
      <EInvoiceType><LabelName>增值税电子普通发票</LabelName></EInvoiceType>
      <GeneralOrSpecialVAT><LabelName>专用</LabelName></GeneralOrSpecialVAT>
    </InherentLabel>
  </Header>
  <TaxSupervisionInfo>
    <InvoiceNumber>2644000001</InvoiceNumber>
    <IssueTime>2026-03-15 10:30:00</IssueTime>
    <TaxBureauName>国家税务总局清远市税务局</TaxBureauName>
  </TaxSupervisionInfo>
  <EInvoiceData>
    <SellerInformation>
      <SellerName>测试销售公司</SellerName>
      <SellerIdNum>91441200MA5XXXXX</SellerIdNum>
      <SellerAddr>广东省清远市</SellerAddr>
      <SellerTelNum>0763-1234567</SellerTelNum>
      <SellerBankName>工商银行清远分行</SellerBankName>
      <SellerBankAccNum>1234567890</SellerBankAccNum>
    </SellerInformation>
    <BuyerInformation>
      <BuyerName>测试购买公司</BuyerName>
      <BuyerIdNum>91441200MA5YYYYY</BuyerIdNum>
      <BuyerAddr></BuyerAddr>
      <BuyerTelNum></BuyerTelNum>
    </BuyerInformation>
    <BasicInformation>
      <TotalAmWithoutTax>1000.00</TotalAmWithoutTax>
      <TotalTaxAm>60.00</TotalTaxAm>
      <TotalTax-includedAmount>1060.00</TotalTax-includedAmount>
      <TotalTax-includedAmountInChinese>壹仟零陆拾元整</TotalTax-includedAmountInChinese>
      <Drawer>张三</Drawer>
    </BasicInformation>
    <IssuItemInformation>
      <ItemName>餐饮服务</ItemName>
      <SpecMod>标准</SpecMod>
      <MeaUnits>次</MeaUnits>
      <Quantity>1</Quantity>
      <UnPrice>1000.00</UnPrice>
      <Amount>1000.00</Amount>
      <TaxRate>0.06</TaxRate>
      <ComTaxAm>60.00</ComTaxAm>
    </IssuItemInformation>
  </EInvoiceData>
</root>
"""


class TestXmlToMarkdown:
    """测试 XML 发票转 Markdown"""

    def test_xml_conversion_basic(self, tmp_path):
        """基本 XML 转 Markdown 功能"""
        xml_file = tmp_path / "invoice.xml"
        xml_file.write_text(SAMPLE_XML, encoding="utf-8")

        result = xml_to_markdown(xml_file)
        assert "# 电子发票" in result
        assert "2644000001" in result
        assert "2026-03-15" in result
        assert "测试销售公司" in result
        assert "测试购买公司" in result

    def test_xml_conversion_amount(self, tmp_path):
        """金额信息正确提取"""
        xml_file = tmp_path / "invoice.xml"
        xml_file.write_text(SAMPLE_XML, encoding="utf-8")

        result = xml_to_markdown(xml_file)
        assert "1000.00" in result
        assert "60.00" in result
        assert "1060.00" in result
        assert "壹仟零陆拾元整" in result

    def test_xml_conversion_items(self, tmp_path):
        """发票明细正确提取"""
        xml_file = tmp_path / "invoice.xml"
        xml_file.write_text(SAMPLE_XML, encoding="utf-8")

        result = xml_to_markdown(xml_file)
        assert "餐饮服务" in result
        assert "6%" in result  # tax rate display (0.06 * 100 = 6%)

    def test_xml_conversion_structure(self, tmp_path):
        """Markdown 结构完整性"""
        xml_file = tmp_path / "invoice.xml"
        xml_file.write_text(SAMPLE_XML, encoding="utf-8")

        result = xml_to_markdown(xml_file)
        assert "## 销售方" in result
        assert "## 购买方" in result
        assert "## 金额" in result
        assert "## 发票明细" in result
