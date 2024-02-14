import Mitt from 'mitt';

export const emitter = Mitt();

export function bind_handlers(handlers) {
    Object.entries(handlers).forEach(([eventName, handler]) => {
        if (typeof handler === 'function') {
            emitter.on(eventName, handler);
        }
    });
}

export function unbind_handlers(handlers) {
    Object.entries(handlers).forEach(([eventName, handler]) => {
        if (typeof handler === 'function') {
            emitter.off(eventName, handler);
        }
    });
}
