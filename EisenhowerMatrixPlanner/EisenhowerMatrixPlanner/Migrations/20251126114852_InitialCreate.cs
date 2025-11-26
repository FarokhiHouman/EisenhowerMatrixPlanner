using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace EisenhowerMatrixPlanner.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Tasks",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "TEXT", nullable: false),
                    Title = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false),
                    Description = table.Column<string>(type: "TEXT", maxLength: 1000, nullable: false),
                    Importance = table.Column<int>(type: "INTEGER", nullable: false),
                    Urgency = table.Column<int>(type: "INTEGER", nullable: false),
                    Deadline = table.Column<DateTime>(type: "TEXT", nullable: true),
                    IsCompleted = table.Column<bool>(type: "INTEGER", nullable: false),
                    IsInProgress = table.Column<bool>(type: "INTEGER", nullable: false),
                    CanvasX = table.Column<double>(type: "REAL", nullable: false),
                    CanvasY = table.Column<double>(type: "REAL", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Tasks", x => x.Id);
                });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "Tasks");
        }
    }
}
