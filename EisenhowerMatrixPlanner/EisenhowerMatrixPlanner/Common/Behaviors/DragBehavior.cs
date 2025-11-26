// Common/Behaviors/DragBehavior.cs
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

using EisenhowerMatrixPlanner.Core.Entities;
using EisenhowerMatrixPlanner.Services;

using Microsoft.Extensions.DependencyInjection;


namespace EisenhowerMatrixPlanner.Common.Behaviors;
public static class DragBehavior {
	public static readonly DependencyProperty IsDragEnabledProperty =
		DependencyProperty.RegisterAttached("IsDragEnabled",
											typeof(bool),
											typeof(DragBehavior),
											new PropertyMetadata(defaultValue: false, OnIsDragEnabledChanged));
	private static Point _startPoint;
	private static bool _isDragging;
	public static bool GetIsDragEnabled(DependencyObject obj) => (bool)obj.GetValue(IsDragEnabledProperty);
	public static void SetIsDragEnabled(DependencyObject obj, bool value) => obj.SetValue(IsDragEnabledProperty, value);

	private static void OnIsDragEnabledChanged(DependencyObject d, DependencyPropertyChangedEventArgs e) {
		if (d is UIElement element) {
			if ((bool)e.NewValue) {
				element.MouseLeftButtonDown += Element_MouseLeftButtonDown;
				element.MouseMove           += Element_MouseMove;
				element.MouseLeftButtonUp   += Element_MouseLeftButtonUp;
			} else {
				element.MouseLeftButtonDown -= Element_MouseLeftButtonDown;
				element.MouseMove           -= Element_MouseMove;
				element.MouseLeftButtonUp   -= Element_MouseLeftButtonUp;
			}
		}
	}

	private static void Element_MouseLeftButtonDown(object sender, MouseButtonEventArgs e) {
		if (sender is FrameworkElement element) {
			_startPoint = e.GetPosition(element);
			_isDragging = false;
			element.CaptureMouse();
		}
	}

	private static void Element_MouseMove(object sender, MouseEventArgs e) {
		if (e.LeftButton == MouseButtonState.Pressed    &&
			sender is FrameworkElement frameworkElement &&
			!_isDragging) {
			Vector diff = _startPoint - e.GetPosition(frameworkElement);
			if (Math.Abs(diff.X) > SystemParameters.MinimumHorizontalDragDistance ||
				Math.Abs(diff.Y) > SystemParameters.MinimumVerticalDragDistance) {
				_isDragging = true;
				frameworkElement.CaptureMouse();
			}
		}
		if (_isDragging && sender is FrameworkElement element) {
			Canvas? canvas = FindParent<Canvas>(element);
			if (canvas != null) {
				Point pos = e.GetPosition(canvas);
				Canvas.SetLeft(element, pos.X - element.ActualWidth  / 2);
				Canvas.SetTop(element, pos.Y  - element.ActualHeight / 2);

				// به‌روزرسانی زنده مدل
				if (element.DataContext is TaskItem task) {
					task.CanvasX = pos.X - element.ActualWidth  / 2;
					task.CanvasY = pos.Y - element.ActualHeight / 2;
				}
			}
		}
	}

	private static void Element_MouseLeftButtonUp(object sender, MouseButtonEventArgs e) {
		if (sender is FrameworkElement element && _isDragging) {
			element.ReleaseMouseCapture();
			if (element.DataContext is TaskItem task) {
				Canvas? canvas = FindParent<Canvas>(element);
				if (canvas != null) {
					Point pos = e.GetPosition(canvas);
					task.CanvasX = pos.X - element.ActualWidth  / 2;
					task.CanvasY = pos.Y - element.ActualHeight / 2;
					TaskService? service = App.ServiceProvider?.GetRequiredService<TaskService>();
					service?.UpdateCanvasPosition(task, canvas.ActualWidth, canvas.ActualHeight);

					// ذخیره در دیتابیس
					_ = Task.Run(async () => await service?.UpdateTaskAsync(task));
				}
			}
			_isDragging = false;
		}
	}

	private static T? FindParent<T>(DependencyObject child)
		where T : DependencyObject {
		DependencyObject? parent = VisualTreeHelper.GetParent(child);
		while (parent != null &&
			   parent is not T) {
			parent = VisualTreeHelper.GetParent(parent);
		}
		return parent as T;
	}
}