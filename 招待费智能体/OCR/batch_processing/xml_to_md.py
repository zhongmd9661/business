"""发票 XML 转 Markdown"""
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from loguru import logger


def xml_to_markdown(xml_path: Path) -> str:
    """将全电发票 XML 转换为 Markdown 格式"""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    md_lines = []

    # 发票基本信息
    invoice_number = root.findtext("TaxSupervisionInfo/InvoiceNumber", "")
    issue_time = root.findtext("TaxSupervisionInfo/IssueTime", "")
    md_lines.append(f"# 电子发票\n\n")
    md_lines.append(f"| 项目 | 内容 |")
    md_lines.append(f"|------|------|")
    md_lines.append(f"| 发票号码 | {invoice_number} |")
    md_lines.append(f"| 开票日期 | {issue_time} |")
    md_lines.append(f"| 发票类型 | {root.findtext('Header/InherentLabel/EInvoiceType/LabelName', '')} |")
    md_lines.append(f"| 发票性质 | {root.findtext('Header/InherentLabel/GeneralOrSpecialVAT/LabelName', '')} |")
    md_lines.append(f"| 税局 | {root.findtext('TaxSupervisionInfo/TaxBureauName', '')} |")
    md_lines.append(f"\n")

    # 销售方
    md_lines.append(f"## 销售方\n\n")
    md_lines.append(f"| 项目 | 内容 |")
    md_lines.append(f"|------|------|")
    md_lines.append(f"| 名称 | {root.findtext('EInvoiceData/SellerInformation/SellerName', '')} |")
    md_lines.append(f"| 纳税人识别号 | {root.findtext('EInvoiceData/SellerInformation/SellerIdNum', '')} |")
    md_lines.append(f"| 地址 | {root.findtext('EInvoiceData/SellerInformation/SellerAddr', '')} |")
    md_lines.append(f"| 电话 | {root.findtext('EInvoiceData/SellerInformation/SellerTelNum', '')} |")
    md_lines.append(f"| 开户行 | {root.findtext('EInvoiceData/SellerInformation/SellerBankName', '')} |")
    md_lines.append(f"| 账号 | {root.findtext('EInvoiceData/SellerInformation/SellerBankAccNum', '')} |")
    md_lines.append(f"\n")

    # 购买方
    md_lines.append(f"## 购买方\n\n")
    md_lines.append(f"| 项目 | 内容 |")
    md_lines.append(f"|------|------|")
    md_lines.append(f"| 名称 | {root.findtext('EInvoiceData/BuyerInformation/BuyerName', '')} |")
    md_lines.append(f"| 纳税人识别号 | {root.findtext('EInvoiceData/BuyerInformation/BuyerIdNum', '')} |")
    md_lines.append(f"| 地址 | {root.findtext('EInvoiceData/BuyerInformation/BuyerAddr', '') or ''} |")
    md_lines.append(f"| 电话 | {root.findtext('EInvoiceData/BuyerInformation/BuyerTelNum', '') or ''} |")
    md_lines.append(f"\n")

    # 金额
    md_lines.append(f"## 金额\n\n")
    md_lines.append(f"| 项目 | 内容 |")
    md_lines.append(f"|------|------|")
    md_lines.append(f"| 不含税金额 | {root.findtext('EInvoiceData/BasicInformation/TotalAmWithoutTax', '')} 元 |")
    md_lines.append(f"| 税额 | {root.findtext('EInvoiceData/BasicInformation/TotalTaxAm', '')} 元 |")
    md_lines.append(f"| 价税合计 | {root.findtext('EInvoiceData/BasicInformation/TotalTax-includedAmount', '')} 元 |")
    md_lines.append(f"| 大写金额 | {root.findtext('EInvoiceData/BasicInformation/TotalTax-includedAmountInChinese', '')} |")
    md_lines.append(f"| 开票人 | {root.findtext('EInvoiceData/BasicInformation/Drawer', '')} |")
    md_lines.append(f"\n")

    # 明细
    md_lines.append(f"## 发票明细\n\n")
    md_lines.append(f"| 商品名称 | 规格 | 单位 | 数量 | 单价 | 金额 | 税率 | 税额 |")
    md_lines.append(f"|----------|------|------|------|------|------|------|------|")
    for item in root.findall("EInvoiceData/IssuItemInformation"):
        md_lines.append(
            f"| {item.findtext('ItemName', '')} | "
            f"{item.findtext('SpecMod', '') or ''} | "
            f"{item.findtext('MeaUnits', '')} | "
            f"{item.findtext('Quantity', '')} | "
            f"{item.findtext('UnPrice', '')} | "
            f"{item.findtext('Amount', '')} | "
            f"{float(item.findtext('TaxRate', '0')) * 100:.0f}% | "
            f"{item.findtext('ComTaxAm', '')} |"
        )
    md_lines.append(f"\n")

    return "\n".join(md_lines)


def convert_xml_files(xml_dir: Path, output_dir: Path) -> list[Path]:
    """转换目录下所有 XML 文件为 Markdown"""
    results = []
    for xml_file in xml_dir.glob("*.xml"):
        try:
            md_content = xml_to_markdown(xml_file)
            md_file = output_dir / f"{xml_file.stem}.md"
            md_file.write_text(md_content, encoding="utf-8")
            logger.info(f"Converted: {xml_file.name} -> {md_file.name}")
            results.append(md_file)
        except Exception as e:
            logger.error(f"Failed to convert {xml_file.name}: {e}")
    return results
