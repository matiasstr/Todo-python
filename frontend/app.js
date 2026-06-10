(function () {
  "use strict";

  angular.module("todoApp", []).controller("TodoController", TodoController);

  TodoController.$inject = ["$http", "$window"];

  function TodoController($http, $window) {
    var vm = this;
    var apiBase = "/api";

    vm.mode = "login";
    vm.auth = {};
    vm.session = loadSession();
    vm.currentUser = vm.session ? vm.session.user : null;
    vm.tasks = [];
    vm.newTaskTitle = "";
    vm.error = "";
    vm.notice = "";

    vm.submitAuth = submitAuth;
    vm.logout = logout;
    vm.createTask = createTask;
    vm.updateTask = updateTask;
    vm.deleteTask = deleteTask;
    vm.pendingCount = pendingCount;

    if (vm.currentUser) {
      loadTasks();
    }

    function submitAuth() {
      clearMessages();

      var endpoint = vm.mode === "login" ? "/auth/login" : "/auth/register";
      var payload = {
        name: vm.auth.name,
        email: vm.auth.email,
        password: vm.auth.password
      };

      $http.post(apiBase + endpoint, payload).then(function (response) {
        vm.session = {
          user: response.data.user,
          token: response.data.token
        };
        vm.currentUser = vm.session.user;
        saveSession(vm.session);
        vm.auth = {};
        vm.notice = response.data.message;
        loadTasks();
      }).catch(showError);
    }

    function logout() {
      vm.currentUser = null;
      vm.session = null;
      vm.tasks = [];
      vm.newTaskTitle = "";
      $window.localStorage.removeItem("todo_session");
      clearMessages();
    }

    function loadTasks() {
      clearMessages();

      $http.get(apiBase + "/tasks", authConfig()).then(function (response) {
        vm.tasks = response.data.tasks;
      }).catch(showError);
    }

    function createTask() {
      clearMessages();

      var title = String(vm.newTaskTitle || "").trim();
      if (!title) {
        vm.error = "Task title is required.";
        return;
      }

      $http.post(apiBase + "/tasks", {
        title: title
      }, authConfig()).then(function (response) {
        vm.tasks.unshift(response.data.task);
        vm.newTaskTitle = "";
        vm.notice = "Task added.";
      }).catch(showError);
    }

    function updateTask(task) {
      clearMessages();

      $http.put(apiBase + "/tasks/" + task.id, {
        title: task.title,
        completed: task.completed
      }, authConfig()).then(function (response) {
        angular.extend(task, response.data.task);
      }).catch(showError);
    }

    function deleteTask(task) {
      clearMessages();

      $http.delete(apiBase + "/tasks/" + task.id, authConfig()).then(function () {
        vm.tasks = vm.tasks.filter(function (item) {
          return item.id !== task.id;
        });
        vm.notice = "Task deleted.";
      }).catch(showError);
    }

    function pendingCount() {
      return vm.tasks.filter(function (task) {
        return !task.completed;
      }).length;
    }

    function clearMessages() {
      vm.error = "";
      vm.notice = "";
    }

    function showError(response) {
      if (response.status === 401) {
        logout();
      }

      vm.error = response.data && response.data.error
        ? response.data.error
        : "Something went wrong.";
    }

    function authConfig() {
      return {
        headers: {
          Authorization: "Bearer " + vm.session.token
        }
      };
    }

    function saveSession(session) {
      $window.localStorage.setItem("todo_session", angular.toJson(session));
    }

    function loadSession() {
      var raw = $window.localStorage.getItem("todo_session");
      var session;

      if (!raw) {
        return null;
      }

      try {
        session = angular.fromJson(raw);
      } catch (error) {
        $window.localStorage.removeItem("todo_session");
        return null;
      }

      if (!session || !session.user || !session.token) {
        $window.localStorage.removeItem("todo_session");
        return null;
      }

      return session;
    }
  }
}());
