using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

namespace HenryLab
{
    /// <summary>
    /// Simulates XRSocketInteractor insertion / removal events.
    /// In real VR, dropping an object into a socket zone fires
    /// <c>selectEntered</c>; pulling it out fires <c>selectExited</c>.
    /// This action reproduces the same events programmatically so
    /// that automated test plans can exercise socket-based logic
    /// without relying on physics overlap detection.
    /// </summary>
    public class SocketAction : BaseAction
    {
        public enum Mode { Insert, Remove }

        private readonly XRSocketInteractor _socket;
        private readonly Mode _mode;

        public SocketAction(XRSocketInteractor socket, Mode mode)
        {
            _socket = socket;
            _mode = mode;
            Name = mode == Mode.Insert ? "SocketInsertAction" : "SocketRemoveAction";
        }

        public override async Task Execute()
        {
            await base.Execute();

            if (_socket == null)
            {
                Debug.LogWarning($"[{Name}] Socket is null — skipping.");
                return;
            }

            var playerObj = EntityManager.Instance.vrexplorerMono.gameObject;
            XRDirectInteractor interactor;
            if (!playerObj.TryGetComponent(out interactor))
            {
                interactor = playerObj.AddComponent<XRDirectInteractor>();
            }

            if (_mode == Mode.Insert)
            {
                var args = new SelectEnterEventArgs { interactorObject = interactor };
                _socket.selectEntered.Invoke(args);
                Debug.Log($"[SocketAction] Insert simulated on {_socket.gameObject.name}");
            }
            else
            {
                var args = new SelectExitEventArgs { interactorObject = interactor };
                _socket.selectExited.Invoke(args);
                Debug.Log($"[SocketAction] Remove simulated on {_socket.gameObject.name}");
            }
        }
    }
}
