// Core/Entities/TaskItem.cs
using CommunityToolkit.Mvvm.ComponentModel;


namespace EisenhowerMatrixPlanner.Core.Entities;
public partial class TaskItem : ObservableObject {
	[ObservableProperty]
	private Guid _id = Guid.NewGuid();
	[ObservableProperty]
	private string _title = string.Empty;
	[ObservableProperty]
	private string _description = string.Empty;

	// 1 تا 10
	[ObservableProperty]
	private int _importance = 5;
	[ObservableProperty]
	private int _urgency = 5;
	[ObservableProperty]
	private DateTime? _deadline;
	[ObservableProperty]
	private bool _isCompleted;
	[ObservableProperty]
	private bool _isInProgress;

	// موقعیت محاسبه‌شده روی Canvas (فقط برای View)
	[ObservableProperty]
	private double _canvasX;
	[ObservableProperty]
	private double _canvasY;
	public TaskItem() { }

	public TaskItem(string title, int importance = 5, int urgency = 5) {
		Title      = title;
		Importance = importance;
		Urgency    = urgency;
	}
}