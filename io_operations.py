"""
流程图工具的保存和读取功能
"""
import json
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import Qt
from logger import logger, print_to_log as print


def save_flowchart(scene, parent_window):
    """
    保存流程图到JSON文件

    Args:
        scene: FlowchartScene对象
        parent_window: 父窗口，用于显示文件对话框

    Returns:
        bool: 保存成功返回True，否则返回False
    """
    logger.info("=== 开始保存流程图 ===")

    try:
        # 获取所有流程图元素
        flowchart_items = []
        connections = []

        # 收集所有元素信息
        logger.debug("\n=== 收集元素信息 ===")
        logger.debug(f"场景中的项目数量: {len(scene.items())}")

        for i, item in enumerate(scene.items()):
            logger.debug(f"\n项目 {i+1}:")
            logger.debug(f"  类型: {item.__class__.__name__}")

            # 检查是否为FlowchartItem实例
            if 'FlowchartItem' in str(item.__class__):
                logger.debug(f"  ✓ 识别为FlowchartItem")

                try:
                    # 尝试访问必要的属性
                    item_id = item.id
                    item_type = item.item_type

                    # 获取文本（支持两种方式）
                    if hasattr(item, 'text_item') and item.text_item:
                        item_text = item.text_item.toPlainText()
                    else:
                        item_text = item.text

                    item_x = item.x()
                    item_y = item.y()

                    # 使用width和height属性而不是rect().width()
                    item_width = item.width
                    item_height = item.height

                    logger.debug(f"  ✓ 成功访问所有属性")
                    logger.debug(f"    - ID: {item_id}")
                    logger.debug(f"    - 类型: {item_type}")
                    logger.debug(f"    - 文本: '{item_text}'")
                    logger.debug(f"    - 位置: ({item_x}, {item_y})")
                    logger.debug(f"    - 尺寸: {item_width}x{item_height}")

                    # 保存元素信息
                    flowchart_item = {
                        "id": item_id,
                        "type": item_type,
                        "x": item_x,
                        "y": item_y,
                        "width": item_width,
                        "height": item_height,
                        "text": item_text
                    }
                    flowchart_items.append(flowchart_item)

                except AttributeError as e:
                    logger.debug(f"  ✗ 缺少属性: {e}")
                except Exception as e:
                    logger.debug(f"  ✗ 访问属性时出错: {e}")
            else:
                logger.debug(f"  - 跳过非FlowchartItem元素")

        logger.debug(f"\n收集到的元素数量: {len(flowchart_items)}")

        # 收集所有连接信息
        logger.debug("\n=== 收集连接信息 ===")
        logger.debug(f"场景中的连接数量: {len(scene.connections)}")

        for i, connection in enumerate(scene.connections):
            logger.debug(f"\n连接 {i+1}:")
            try:
                # 检查连接对象是否有效
                if hasattr(connection, 'start_item') and hasattr(connection, 'end_item'):
                    # 检查是否有标签
                    label = connection.label if hasattr(connection, 'label') else None

                    connection_data = {
                        "start_item_id": connection.start_item.id,
                        "start_point_type": connection.start_point_type,
                        "end_item_id": connection.end_item.id,
                        "end_point_type": connection.end_point_type,
                        "label": label
                    }
                    connections.append(connection_data)

                    logger.debug(f"  ✓ 成功收集连接信息")
                    logger.debug(f"    - 起始元素ID: {connection.start_item.id}")
                    logger.debug(f"    - 起始点类型: {connection.start_point_type}")
                    logger.debug(f"    - 结束元素ID: {connection.end_item.id}")
                    logger.debug(f"    - 结束点类型: {connection.end_point_type}")
                else:
                    logger.debug(f"  ✗ 连接对象无效，缺少必要属性")

            except Exception as e:
                logger.debug(f"  ✗ 收集连接信息失败: {e}")

        logger.debug(f"\n收集到的连接数量: {len(connections)}")

        # 创建JSON数据
        flowchart_data = {
            "version": "1.0",
            "items": flowchart_items,
            "connections": connections
        }

        # 显示要保存的数据
        logger.debug("\n=== 要保存的数据 ===")
        logger.debug(json.dumps(flowchart_data, indent=2, ensure_ascii=False))

        # 显示保存文件对话框
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            parent_window,
            "保存流程图",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            logger.info("用户取消了文件选择")
            return False

        # 确保文件扩展名为.json
        if not file_path.endswith(".json"):
            file_path += ".json"

        try:
            # 保存到JSON文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(flowchart_data, f, indent=2, ensure_ascii=False)

            logger.info(f"\n✓ 成功保存到文件: {file_path}")

            # 验证保存的文件
            with open(file_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
            logger.debug(f"✓ 验证保存的文件:")
            logger.debug(f"  - 版本: {saved_data.get('version')}")
            logger.debug(f"  - 元素数量: {len(saved_data.get('items', []))}")
            logger.debug(f"  - 连接数量: {len(saved_data.get('connections', []))}")

            QMessageBox.information(parent_window, "保存成功",
                                  f"流程图已成功保存到:\n{file_path}\n\n"
                                  f"保存统计:\n"
                                  f"- 元素数量: {len(flowchart_items)}\n"
                                  f"- 连接数量: {len(connections)}")
            return True

        except Exception as e:
            logger.debug(f"✗ 保存文件失败: {e}")
            QMessageBox.warning(parent_window, "保存失败", f"保存文件时出错:\n{str(e)}")
            return False

    except Exception as e:
        logger.debug(f"✗ 保存流程整体失败: {e}")
        import traceback
        traceback.print_exc()
        QMessageBox.warning(parent_window, "保存失败", f"保存流程图时出错:\n{str(e)}")
        return False

def load_flowchart(scene, parent_window, file_path=None):
    """
    从JSON文件加载流程图

    Args:
        scene: FlowchartScene对象
        parent_window: 父窗口，用于显示文件对话框

    Returns:
        bool: 加载成功返回True，否则返回False
    """
    logger.info("=== 开始加载流程图 ===")

    try:
        if file_path is None:
            # 动态导入需要的类
            logger.debug("尝试导入FlowchartItem和ConnectionLine...")
            from main import FlowchartItem, ConnectionLine
            logger.debug("✓ 成功导入所需类")

            # 显示打开文件对话框
            file_dialog = QFileDialog()
            file_path, _ = file_dialog.getOpenFileName(
                parent_window,
                "打开流程图",
                "",
                "JSON Files (*.json);;All Files (*)"
            )

            if not file_path:
                logger.info("用户取消了文件选择")
                return False
        else:
            from main import FlowchartItem, ConnectionLine
        logger.debug(f"选择的文件: {file_path}")

        # 读取JSON文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                flowchart_data = json.load(f)
            logger.debug("✓ 成功读取JSON文件")
            # logger.debug(f"文件内容: {json.dumps(flowchart_data, indent=2, ensure_ascii=False)}")
        except Exception as e:
            logger.debug(f"✗ 读取JSON文件失败: {e}")
            QMessageBox.warning(parent_window, "读取失败", f"无法读取文件:\n{str(e)}")
            return False

        # 验证文件格式
        if "version" not in flowchart_data or "items" not in flowchart_data or "connections" not in flowchart_data:
            logger.debug("✗ 文件格式错误")
            QMessageBox.warning(parent_window, "文件格式错误", "无效的流程图文件格式")
            return False

        # 清空当前场景
        scene.clear()
        scene.connections.clear()
        logger.debug("✓ 清空当前场景")

        # 启用批量加载模式，避免每次addItem都更新画布（性能优化）
        if hasattr(scene, 'batch_loading'):
            scene.batch_loading = True
            logger.debug("✓ 启用批量加载模式")

        # 创建元素字典，用于快速查找
        item_dict = {}

        # 创建元素
        logger.debug(f"\n=== 加载元素 ===")
        logger.debug(f"元素数量: {len(flowchart_data['items'])}")

        for i, item_data in enumerate(flowchart_data["items"]):
            logger.debug(f"\n加载元素 {i+1}:")
            logger.debug(f"  数据: {item_data}")

            try:
                item_type = item_data["type"]
                x = item_data["x"]
                y = item_data["y"]
                width = item_data.get("width", 125)  # 使用与FlowchartItem一致的默认值
                height = item_data.get("height", 75)  # 使用与FlowchartItem一致的默认值

                # 创建流程图元素
                item = FlowchartItem(item_type, x, y, width, height)
                item.id = item_data["id"]

                # 设置文本
                item_text = item_data.get("text", "")
                item.setText(item_text)

                scene.addItem(item)
                item_dict[item.id] = item

                # 手动更新连接点位置（解决加载文件后连接点位置不正确的问题）
                item.update_connection_points()

                # 确保连接点在最上层（但不要设置过高，以免影响事件处理）
                for point in item.connection_points.values():
                    point.setZValue(10)  # 恢复到原始的z值

                # 调试：检查连接点是否正确创建
                logger.debug(f"  ✓ 成功创建元素: {item.id}")
                logger.debug(f"  ✓ 元素类型: {item_type}")
                logger.debug(f"  ✓ 元素位置: ({x}, {y})")
                logger.debug(f"  ✓ 元素文本: '{item_text}'")
                logger.debug(f"  ✓ 连接点数量: {len(item.connection_points)}")
                logger.debug(f"  ✓ 元素类型属性: {item.item_type}")
                logger.debug(f"  ✓ 文本项内容: '{item.text_item.toPlainText()}'")

            except Exception as e:
                logger.debug(f"  ✗ 创建元素失败: {e}")
                import traceback
                traceback.print_exc()

        # 创建连接
        logger.debug(f"\n=== 加载连接 ===")
        # 先收集所有连接数据，稍后在所有元素都完全加载后创建连接
        connections_to_create = []
        for i, connection_data in enumerate(flowchart_data["connections"]):
            logger.debug(f"\n收集连接数据 {i+1}:")
            logger.debug(f"  数据: {connection_data}")
            connections_to_create.append(connection_data)
        
        logger.debug(f"\n=== 所有元素加载完成，开始创建连接 ===")
        logger.debug(f"连接数量: {len(connections_to_create)}")
        
        # 延迟创建连接，确保所有元素都已完全加载
        for i, connection_data in enumerate(connections_to_create):
            logger.debug(f"\n创建连接 {i+1}:")
            logger.debug(f"  数据: {connection_data}")

            try:
                start_item_id = connection_data["start_item_id"]
                start_point_type = connection_data["start_point_type"]
                end_item_id = connection_data["end_item_id"]
                end_point_type = connection_data["end_point_type"]

                # 查找起始和结束元素
                if start_item_id in item_dict and end_item_id in item_dict:
                    start_item = item_dict[start_item_id]
                    end_item = item_dict[end_item_id]

                    logger.debug(f"  ✓ 找到起始元素: {start_item_id}")
                    logger.debug(f"  ✓ 找到结束元素: {end_item_id}")

                    # 创建连接线
                    connection = ConnectionLine(
                        start_item,
                        start_point_type,
                        end_item,
                        end_point_type
                    )
                    scene.addItem(connection)
                    scene.connections.append(connection)

                    # 恢复标签信息
                    if "label" in connection_data and connection_data["label"]:
                        connection.label = connection_data["label"]
                        connection.create_label()

                    logger.debug(f"  ✓ 成功创建连接")
                    if connection.label:
                        logger.debug(f"    - 标签: {connection.label}")
                else:
                    logger.debug(f"  ✗ 找不到连接的元素")
                    logger.debug(f"    - 起始元素ID: {start_item_id} {'存在' if start_item_id in item_dict else '不存在'}")
                    logger.debug(f"    - 结束元素ID: {end_item_id} {'存在' if end_item_id in item_dict else '不存在'}")

            except Exception as e:
                logger.debug(f"  ✗ 创建连接失败: {e}")
                import traceback
                traceback.print_exc()

        # 在所有连接创建完成后，立即更新所有连接的路径
        logger.debug("\n=== 更新所有连接路径 ===")
        for connection in scene.connections:
            connection.update_path()
        logger.debug("✓ 所有连接路径已更新")
        
        # 禁用批量加载模式
        if hasattr(scene, 'batch_loading'):
            scene.batch_loading = False
            logger.debug("✓ 禁用批量加载模式")
        
        # 更新画布大小以适应加载的元素
        if hasattr(scene, 'update_scene_bounds'):
            scene.update_scene_bounds()
            logger.debug("✓ 画布大小已更新")
        
        # 让视图自动适应场景范围，确保所有元素可见
        if hasattr(parent_window, 'view'):
            view = parent_window.view
            # 获取场景的实际边界（包含所有元素）
            scene_rect = scene.sceneRect()
            logger.debug(f"场景边界: x={scene_rect.x():.0f}, y={scene_rect.y():.0f}, "
                        f"w={scene_rect.width():.0f}, h={scene_rect.height():.0f}")
            
            # 重置视图变换
            view.resetTransform()
            
            # 确保视图显示整个场景（稍微放大一点以提供边距）
            view.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
            
            # 稍微缩小一点，留出边距（但不要太小）
            view.scale(0.95, 0.95)
            
            logger.debug("✓ 视图已适应场景范围")
        
        # 验证加载结果
        logger.debug(f"\n=== 加载结果 ===")
        logger.debug(f"创建的元素数量: {len(item_dict)}")
        logger.debug(f"创建的连接数量: {len(scene.connections)}")
        logger.debug(f"场景中的项目数量: {len(scene.items())}")

        # 检查场景中的项目类型
        item_types = {}
        for item in scene.items():
            item_class = item.__class__.__name__
            item_types[item_class] = item_types.get(item_class, 0) + 1

        logger.debug(f"场景中的项目类型: {item_types}")
        
        # 显示成功消息
        success_msg = f"流程图已成功从:\n{file_path} 加载\n\n"
        success_msg += f"加载统计:\n"
        success_msg += f"- 元素数量: {len(item_dict)}\n"
        success_msg += f"- 连接数量: {len(scene.connections)}"

        QMessageBox.information(parent_window, "加载成功", success_msg)
        logger.debug("=== 加载完成 ===")
        return True

    except Exception as e:
        logger.debug(f"✗ 加载流程整体失败: {e}")
        import traceback
        traceback.print_exc()
        QMessageBox.warning(parent_window, "加载失败", f"加载文件时出错:\n{str(e)}")
        return False
