using System;
using System.Windows;
using Dienstplaner.ViewModels;

namespace Dienstplaner
{
    public partial class MainWindow : Window
    {
        public MainWindow(MainViewModel viewModel)
        {
            if (viewModel == null)
                throw new ArgumentNullException("viewModel");

            InitializeComponent();
            DataContext = viewModel;
        }
    }
}
