package api;

public class APINoSuchDataException extends Exception {
	private static final long serialVersionUID = -2592629196341721497L;

	public APINoSuchDataException(String message) {
		super(message);
	}

}
